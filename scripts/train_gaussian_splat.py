#!/usr/bin/env python3
"""
Training script for 3D Gaussian Splats using gsplat-mlx
Trains on iPhone video frames with SfM camera poses
Uses the low-level differentiable accumulate path (not the tile-based rasterizer)
"""

import argparse
import json
import logging
import os
import tomllib
import time
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from PIL import Image
from dataclasses import dataclass

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optimizers

# Add gsplat-mlx to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "gsplat-mlx" / "src"))

from gsplat_mlx.core.covariance import quat_scale_to_covar_preci
from gsplat_mlx.core.projection import fully_fused_projection
from gsplat_mlx.core.spherical_harmonics import spherical_harmonics
from gsplat_mlx.core.accumulate import accumulate
from gsplat_mlx.exporter import export_splats

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CameraIntrinsics:
    """Camera intrinsic parameters"""
    fx: float
    fy: float
    cx: float
    cy: float
    width: int
    height: int


@dataclass
class CameraPose:
    """Camera pose (world-to-camera transformation)"""
    viewmat: np.ndarray  # [4, 4]
    intrinsics: CameraIntrinsics


def load_config(config_path: str) -> dict:
    """Load configuration from TOML file"""
    with open(config_path, 'rb') as f:
        return tomllib.load(f)


def load_frames(frames_dir: str, downscale: int = 1) -> List[np.ndarray]:
    """Load all frame images from directory"""
    logger.info(f"Loading frames from {frames_dir} (downscale={downscale})")
    frames_path = Path(frames_dir)
    frame_files = sorted(frames_path.glob("frame_*.png"))

    frames = []
    for frame_file in frame_files:
        img = Image.open(frame_file).convert('RGB')

        # Downscale if needed
        if downscale > 1:
            new_width = img.width // downscale
            new_height = img.height // downscale
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        frame = np.array(img, dtype=np.float32) / 255.0
        frames.append(frame)
        logger.info(f"  Loaded {frame_file.name} {frame.shape}")

    logger.info(f"Total frames loaded: {len(frames)}")
    return frames


def load_camera_intrinsics(sfm_dir: str) -> CameraIntrinsics:
    """Load camera intrinsics from cameras.json"""
    cameras_path = Path(sfm_dir) / "cameras.json"
    with open(cameras_path, 'r') as f:
        data = json.load(f)

    camera = data['cameras']['0']  # Use first camera
    intrinsics = CameraIntrinsics(
        fx=camera['focal_length_x'],
        fy=camera['focal_length_y'],
        cx=camera['principal_point_x'],
        cy=camera['principal_point_y'],
        width=camera['image_width'],
        height=camera['image_height'],
    )
    logger.info(f"Loaded camera intrinsics: {intrinsics}")
    return intrinsics


def load_camera_poses(sfm_dir: str, intrinsics: CameraIntrinsics) -> List[Tuple[str, CameraPose]]:
    """Load camera poses from poses.json"""
    poses_path = Path(sfm_dir) / "poses.json"
    with open(poses_path, 'r') as f:
        data = json.load(f)

    camera_poses = []
    for pose_id, pose_data in data['poses'].items():
        R = np.array(pose_data['R'], dtype=np.float32)
        t = np.array(pose_data['t'], dtype=np.float32)

        # Convert R,t to 4x4 viewmat (world-to-camera)
        viewmat = np.eye(4, dtype=np.float32)
        viewmat[:3, :3] = R
        viewmat[:3, 3] = t

        pose = CameraPose(viewmat=viewmat, intrinsics=intrinsics)
        camera_poses.append((pose_id, pose))

    logger.info(f"Loaded {len(camera_poses)} camera poses")
    return camera_poses


def create_intrinsic_matrix(intrinsics: CameraIntrinsics) -> np.ndarray:
    """Create 3x3 camera intrinsic matrix K"""
    K = np.array([
        [intrinsics.fx, 0, intrinsics.cx],
        [0, intrinsics.fy, intrinsics.cy],
        [0, 0, 1]
    ], dtype=np.float32)
    return K


def initialize_gaussians(num_gaussians: int, config: dict) -> Dict[str, mx.array]:
    """Initialize Gaussian parameters"""
    init_scale_log = config['training']['init_scale_log']
    init_opacity = config['training']['init_opacity']
    sh_degree = config['training']['sh_degree']

    logger.info(f"Initializing {num_gaussians} Gaussians")

    # Position: random in unit cube
    means = mx.random.uniform(-1, 1, (num_gaussians, 3))

    # Rotation: identity quaternions (w, x, y, z)
    quats = mx.concatenate([mx.ones((num_gaussians, 1)), mx.zeros((num_gaussians, 3))], axis=1)

    # Scale: log-space (will be exponentiated in loss)
    scales = mx.full((num_gaussians, 3), init_scale_log)

    # Opacity: sigmoid parameter
    opacities = mx.full((num_gaussians,), init_opacity)

    # Spherical harmonics coefficients
    num_sh_coeffs = (sh_degree + 1) ** 2
    sh_coeffs = mx.random.normal((num_gaussians, num_sh_coeffs, 3)) * 0.1

    params = {
        'means': means,
        'quats': quats,
        'scales': scales,
        'opacities': opacities,
        'sh_coeffs': sh_coeffs,
    }

    logger.info("Gaussian parameters initialized")
    return params


def normalize_quaternion(quat):
    """Normalize quaternion"""
    norm = mx.sqrt(mx.sum(quat ** 2, axis=-1, keepdims=True))
    return quat / (norm + 1e-8)


def differentiable_render(
    means: mx.array,
    quats: mx.array,
    scales_exp: mx.array,
    opacities_sig: mx.array,
    sh_coeffs: mx.array,
    viewmat: mx.array,
    K: mx.array,
    width: int,
    height: int,
    sh_degree: int,
) -> mx.array:
    """Render Gaussians using the differentiable accumulate path.

    This is fully differentiable and memory-efficient, unlike the
    tile-based rasterizer which uses non-differentiable NumPy code.
    """
    N = means.shape[0]
    C = 1  # single camera

    # --- Step 1: Covariance from quats + scales ---
    covars, _ = quat_scale_to_covar_preci(
        quats, scales_exp, compute_covar=True, compute_preci=False, triu=False,
    )  # [N, 3, 3]

    # --- Step 2: Project ---
    # Add camera dimension if not present
    if viewmat.ndim == 2:
        viewmat = viewmat[None, ...]  # [1, 4, 4]
    if K.ndim == 2:
        K = K[None, ...]  # [1, 3, 3]

    radii, means2d, depths, conics, _ = fully_fused_projection(
        means, covars, viewmat, K, width, height,
        eps2d=0.3, near_plane=0.01, far_plane=1e10,
        calc_compensations=False, camera_model="pinhole",
    )
    # radii: [C, N, 2], means2d: [C, N, 2], depths: [C, N], conics: [C, N, 3]

    # --- Step 3: SH colours ---
    # Camera position from viewmat: -R^T @ t
    R = viewmat[0, :3, :3]  # [3, 3]
    t = viewmat[0, :3, 3]   # [3]
    campos = -mx.einsum("ji,j->i", R, t)  # [3]

    dirs = means - campos[None, :]  # [N, 3]
    dirs_norm = mx.sqrt(mx.sum(dirs * dirs, axis=-1, keepdims=True))
    dirs = dirs / mx.maximum(dirs_norm, mx.array(1e-8))

    # spherical_harmonics expects [C, N, K, 3] coeffs and [C, N, 3] dirs
    coeffs_b = mx.expand_dims(sh_coeffs, 0)  # [1, N, K, 3]
    dirs_b = mx.expand_dims(dirs, 0)  # [1, N, 3]
    rgb = spherical_harmonics(sh_degree, dirs_b, coeffs_b)  # [1, N, 3]
    rgb = mx.maximum(rgb + 0.5, 0.0)  # bias + clamp

    # --- Step 4: Build brute-force intersection lists ---
    # Filter to Gaussians with positive depth and non-zero radii.
    valid_mask = (depths[0] > 0.0)  # [N]
    valid_r = mx.minimum(radii[0, :, 0], radii[0, :, 1])  # [N]
    valid_mask = valid_mask & (valid_r > 0)

    # Sort Gaussians by depth for correct front-to-back compositing
    depth_vals = depths[0]  # [N]
    sorted_order = mx.argsort(depth_vals)  # [N]

    # Build all (gaussian, pixel) pairs for valid Gaussians
    n_pixels = height * width
    pixel_ids_all = mx.arange(n_pixels)  # [H*W]

    gaussian_ids = mx.repeat(sorted_order, n_pixels)  # [N * n_pixels]
    pixel_ids = mx.tile(pixel_ids_all, (N,))  # [N * n_pixels]
    image_ids = mx.zeros_like(gaussian_ids)  # all camera 0

    # --- Step 5: Accumulate ---
    renders, alphas = accumulate(
        means2d,                       # [C, N, 2]
        conics,                        # [C, N, 3]
        opacities_sig[None, :],        # [C, N] -- broadcast camera dim
        rgb,                           # [C, N, 3]
        gaussian_ids,
        pixel_ids,
        image_ids,
        width,
        height,
    )
    # renders: [C, H, W, 3], alphas: [C, H, W, 1]
    return renders[0]  # [H, W, 3]


def l1_loss(pred: mx.array, target: mx.array) -> mx.array:
    """Element-wise L1 loss, averaged over all elements."""
    return mx.mean(mx.abs(pred - target))


def train_step(
    params: Dict[str, mx.array],
    target_image: mx.array,
    viewmat: mx.array,
    K: mx.array,
    width: int,
    height: int,
    config: dict,
) -> Tuple[mx.array, Dict[str, mx.array]]:
    """Single training step"""
    sh_degree = config['training']['sh_degree']

    def loss_fn(means, quats, scales, opacities, sh_coeffs):
        # Normalize quaternions and apply transformations
        quats_normalized = normalize_quaternion(quats)
        scales_exp = mx.exp(scales)
        opacities_sigmoid = mx.sigmoid(opacities)

        # Render
        rendered = differentiable_render(
            means=means,
            quats=quats_normalized,
            scales_exp=scales_exp,
            opacities_sig=opacities_sigmoid,
            sh_coeffs=sh_coeffs,
            viewmat=viewmat,
            K=K,
            width=width,
            height=height,
            sh_degree=sh_degree,
        )

        # Compute loss
        loss = l1_loss(rendered, target_image)
        return loss

    # Compute loss and gradients
    loss, grads = mx.value_and_grad(
        loss_fn,
        argnums=(0, 1, 2, 3, 4)
    )(
        params['means'],
        params['quats'],
        params['scales'],
        params['opacities'],
        params['sh_coeffs'],
    )

    # Extract gradients
    grad_means, grad_quats, grad_scales, grad_opacities, grad_sh = grads

    # Manual parameter updates with learning rates
    lr_means = config['training']['lr_means']
    lr_quats = config['training']['lr_quats']
    lr_scales = config['training']['lr_scales']
    lr_opacities = config['training']['lr_opacities']
    lr_sh_coeffs = config['training']['lr_sh_coeffs']

    params['means'] = params['means'] - lr_means * grad_means
    params['quats'] = params['quats'] - lr_quats * grad_quats
    params['scales'] = params['scales'] - lr_scales * grad_scales
    params['opacities'] = params['opacities'] - lr_opacities * grad_opacities
    params['sh_coeffs'] = params['sh_coeffs'] - lr_sh_coeffs * grad_sh

    # Force evaluation
    mx.eval(loss)
    mx.eval(*[params[n] for n in params.keys()])

    return loss, params


def train(
    config: dict,
    frames: List[np.ndarray],
    camera_poses: List[Tuple[str, CameraPose]],
    output_dir: str,
) -> Dict[str, mx.array]:
    """Main training loop"""

    num_steps = config['training']['num_steps']
    num_gaussians = config['training']['num_gaussians']
    log_every = config['logging']['log_every_n_steps']
    save_every = config['logging']['save_every_n_steps']

    # Get image dimensions from first frame
    height, width = frames[0].shape[:2]
    logger.info(f"Training on {width}x{height} images with {len(frames)} views")

    # Convert frames to MLX arrays
    mx_frames = [mx.array(f, dtype=mx.float32) for f in frames]

    # Initialize parameters
    params = initialize_gaussians(num_gaussians, config)

    # Prepare camera parameters as MLX arrays
    camera_data = []
    for pose_id, pose in camera_poses:
        viewmat = mx.array(pose.viewmat, dtype=mx.float32)
        K = mx.array(create_intrinsic_matrix(pose.intrinsics), dtype=mx.float32)
        camera_data.append((viewmat, K))

    # Training loop
    logger.info(f"Starting training for {num_steps} steps")
    t0 = time.time()

    for step in range(num_steps):
        # Randomly select a view
        view_idx = int(np.random.randint(0, len(camera_data)))
        viewmat, K = camera_data[view_idx]
        target_image = mx_frames[view_idx]

        loss, params = train_step(
            params, target_image, viewmat, K,
            width, height, config
        )

        # Logging
        if (step + 1) % log_every == 0:
            elapsed = time.time() - t0
            logger.info(f"Step {step + 1}/{num_steps}, Loss: {loss.item():.6f}, Elapsed: {elapsed:.1f}s")

        # Checkpointing
        if (step + 1) % save_every == 0:
            checkpoint_dir = Path(output_dir)
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            checkpoint_file = checkpoint_dir / f"checkpoint_step_{step + 1}.ply"
            logger.info(f"Saving checkpoint to {checkpoint_file}")
            _save_ply(params, checkpoint_file, config)

    logger.info("Training complete")
    return params


def _save_ply(
    params: Dict[str, mx.array],
    output_path: Path,
    config: dict
) -> None:
    """Save Gaussian parameters to PLY file"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert MLX arrays to numpy
    means = np.array(params['means'])
    quats = np.array(params['quats'])
    scales = np.array(params['scales'])
    opacities = np.array(params['opacities'])
    sh_coeffs = np.array(params['sh_coeffs'])

    # Ensure quaternions are normalized
    quat_norms = np.linalg.norm(quats, axis=1, keepdims=True)
    quats = quats / (quat_norms + 1e-8)

    # Exponentiate scales (they're stored in log-space)
    scales_exp = np.exp(scales)

    # Sigmoid opacities
    opacities_sigmoid = 1.0 / (1.0 + np.exp(-opacities))

    # Use gsplat-mlx exporter
    export_splats(
        str(output_path),
        means=means,
        quats=quats,
        scales=scales_exp,
        opacities=opacities_sigmoid,
        sh_coeffs=sh_coeffs,
        write_colors=True,
        sh_degree=config['training']['sh_degree'],
    )
    logger.info(f"Saved PLY to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Train 3D Gaussian Splats")
    parser.add_argument('--config', type=str, default='config.toml',
                        help='Path to config TOML file')
    parser.add_argument('--output', type=str, default=None,
                        help='Output directory for trained model')
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Override output directory if provided
    if args.output:
        config['data']['output_dir'] = args.output

    output_dir = config['data']['output_dir']

    # Load data
    downscale = config['data'].get('downscale', 1)
    frames = load_frames(config['data']['frames_dir'], downscale=downscale)
    intrinsics = load_camera_intrinsics(config['data']['sfm_dir'])
    camera_poses = load_camera_poses(config['data']['sfm_dir'], intrinsics)

    # Scale intrinsics by downscale factor
    if downscale > 1:
        intrinsics.fx /= downscale
        intrinsics.fy /= downscale
        intrinsics.cx /= downscale
        intrinsics.cy /= downscale
        intrinsics.width //= downscale
        intrinsics.height //= downscale

    # Update camera poses with scaled intrinsics
    camera_poses = [(pose_id, CameraPose(pose.viewmat, intrinsics))
                    for pose_id, pose in camera_poses]

    # Filter frames to only those with poses
    registered_indices = {int(pose_id) for pose_id, _ in camera_poses}
    frames_to_use = [frames[i] for i in range(len(frames)) if i in registered_indices]

    # Sort poses by frame index
    camera_poses_sorted = []
    for i in range(len(frames)):
        for pose_id, pose in camera_poses:
            if int(pose_id) == i:
                camera_poses_sorted.append((pose_id, pose))
                break

    camera_poses = camera_poses_sorted[:len(frames_to_use)]

    logger.info(f"Using {len(frames_to_use)} registered frames for training")

    # Train
    trained_params = train(config, frames_to_use, camera_poses, output_dir)

    # Save final model
    output_path = Path(output_dir) / "latest.ply"
    _save_ply(trained_params, output_path, config)

    logger.info(f"Training complete! Model saved to {output_path}")


if __name__ == '__main__':
    main()

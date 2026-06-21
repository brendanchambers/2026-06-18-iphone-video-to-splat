"""
OpenSplat training utility.
"""
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from omegaconf import DictConfig


logger = logging.getLogger(__name__)


def train_splat(
    sparse_model_path: Path,
    images_path: Path,
    output_dir: Path,
    opensplat_bin: Path,
    experiment_name: str,
    config: Optional[DictConfig] = None,
    log_file: Optional[Path] = None,
) -> bool:
    """
    Train a 3D Gaussian splat using OpenSplat.

    Args:
        sparse_model_path: Path to COLMAP sparse model (with cameras.bin, images.bin, points3D.bin)
        images_path: Path to undistorted images from COLMAP
        output_dir: Directory to save output PLY file and checkpoints
        opensplat_bin: Path to OpenSplat binary
        experiment_name: Name of experiment for output filename
        config: Optional OmegaConf config object with OpenSplat parameters
        log_file: Optional path to log file

    Returns:
        True if successful, False otherwise
    """
    sparse_model_path = Path(sparse_model_path)
    images_path = Path(images_path)
    output_dir = Path(output_dir)
    opensplat_bin = Path(opensplat_bin)

    # Validate inputs
    if not sparse_model_path.exists():
        logger.error(f"Sparse model path not found: {sparse_model_path}")
        return False

    if not images_path.exists():
        logger.error(f"Images path not found: {images_path}")
        return False

    if not opensplat_bin.exists():
        logger.error(f"OpenSplat binary not found: {opensplat_bin}")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_filename = f"{experiment_name}_{timestamp}.ply"
        output_path = output_dir / output_filename

        logger.info(f"Training 3D Gaussian Splat")
        logger.info(f"Sparse model: {sparse_model_path}")
        logger.info(f"Images: {images_path}")
        logger.info(f"Output: {output_path}")

        # Build command with OpenSplat parameters
        cmd = [
            str(opensplat_bin),
            str(sparse_model_path),
            "--colmap-image-path", str(images_path),
            "--output", str(output_path),
        ]

        # Add training parameters
        if config and "opensplat" in config:
            splat_config = config.opensplat
            params = [
                ("--num-iters", splat_config.num_iters),
                ("--downscale-factor", splat_config.downscale_factor),
                ("--num-downscales", splat_config.num_downscales),
                ("--resolution-schedule", splat_config.resolution_schedule),
                ("--sh-degree", splat_config.sh_degree),
                ("--sh-degree-interval", splat_config.sh_degree_interval),
                ("--ssim-weight", splat_config.ssim_weight),
                ("--refine-every", splat_config.refine_every),
                ("--warmup-length", splat_config.warmup_length),
                ("--reset-alpha-every", splat_config.reset_alpha_every),
                ("--densify-grad-thresh", splat_config.densify_grad_thresh),
                ("--densify-size-thresh", splat_config.densify_size_thresh),
                ("--stop-screen-size-at", splat_config.stop_screen_size_at),
                ("--split-screen-size", splat_config.split_screen_size),
            ]
            for key, value in params:
                cmd.extend([key, str(value)])

            # Add validation parameters if enabled
            if config and "validation" in config:
                val_config = config.validation
                if val_config.enabled:
                    cmd.extend(["--val"])
                    if val_config.image != "random":
                        cmd.extend(["--val-image", val_config.image])
                    if "val_render_dir" in config.paths:
                        val_render = Path(config.paths.val_render_dir)
                        val_render.mkdir(parents=True, exist_ok=True)
                        cmd.extend(["--val-render", str(val_render)])
        else:
            # Use defaults
            cmd.extend([
                "--num-iters", "1500",
                "--downscale-factor", "1",
                "--num-downscales", "2",
                "--resolution-schedule", "3000",
                "--sh-degree", "3",
                "--sh-degree-interval", "1000",
                "--ssim-weight", "0.2",
                "--refine-every", "100",
                "--warmup-length", "500",
                "--reset-alpha-every", "30",
                "--densify-grad-thresh", "0.0002",
                "--densify-size-thresh", "0.01",
                "--stop-screen-size-at", "4000",
                "--split-screen-size", "0.05",
            ])

        logger.info(f"Running: opensplat")

        # Run OpenSplat with output logging
        with open(log_file, "w") if log_file else None as log_fh:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            for line in process.stdout:
                logger.info(line.rstrip())
                if log_fh:
                    log_fh.write(line + "\n")

            returncode = process.wait()

        if returncode != 0:
            logger.error(f"opensplat failed with return code {returncode}")
            return False

        logger.info(f"Training completed successfully")
        logger.info(f"Output saved to: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error training splat: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Test - this will fail without proper setup
    print("OpenSplat trainer module loaded")

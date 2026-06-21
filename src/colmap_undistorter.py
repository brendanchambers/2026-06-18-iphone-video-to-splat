"""
COLMAP image undistortion utility.
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional
from omegaconf import DictConfig


logger = logging.getLogger(__name__)


def undistort_images(
    image_path: Path,
    input_model_path: Path,
    output_path: Path,
    config: Optional[DictConfig] = None,
    log_file: Optional[Path] = None,
) -> bool:
    """
    Undistort images using COLMAP's image_undistorter.

    Args:
        image_path: Path to directory containing original images
        input_model_path: Path to sparse model (from mapper, typically model_0)
        output_path: Path to save undistorted images and corrected cameras
        config: Optional OmegaConf config object with COLMAP parameters
        log_file: Optional path to log file

    Returns:
        True if successful, False otherwise
    """
    image_path = Path(image_path)
    input_model_path = Path(input_model_path)
    output_path = Path(output_path)

    # Validate inputs
    if not image_path.exists():
        logger.error(f"Image directory not found: {image_path}")
        return False

    if not input_model_path.exists():
        logger.error(f"Input model path not found: {input_model_path}")
        return False

    output_path.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"Undistorting images")
        logger.info(f"Input model: {input_model_path}")
        logger.info(f"Images: {image_path}")
        logger.info(f"Output: {output_path}")

        # Build command with COLMAP parameters
        cmd = [
            "colmap", "image_undistorter",
            "--image_path", str(image_path),
            "--input_path", str(input_model_path),
            "--output_path", str(output_path),
        ]

        if config and "colmap" in config and "undistorter" in config.colmap:
            undist_config = config.colmap.undistorter
            params = [
                ("--output_type", undist_config.output_type),
                ("--copy_policy", undist_config.copy_policy),
                ("--blank_pixels", undist_config.blank_pixels),
                ("--min_scale", undist_config.min_scale),
                ("--max_scale", undist_config.max_scale),
                ("--max_image_size", undist_config.max_image_size),
                ("--num_patch_match_src_images", undist_config.num_patch_match_src_images),
                ("--jpeg_quality", undist_config.jpeg_quality),
            ]
            for key, value in params:
                cmd.extend([key, str(value)])
        else:
            # Use defaults
            cmd.extend([
                "--output_type", "COLMAP",
                "--copy_policy", "copy",
                "--blank_pixels", "0",
                "--min_scale", "0.2",
                "--max_scale", "2",
                "--max_image_size", "-1",
                "--num_patch_match_src_images", "20",
                "--jpeg_quality", "-1",
            ])

        logger.info(f"Running: colmap image_undistorter")

        # Run COLMAP with output logging
        with open(log_file, "a") if log_file else None as log_fh:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            for line in process.stdout:
                logger.info(line.rstrip())
                if log_fh:
                    log_fh.write(line)

            returncode = process.wait()

        if returncode != 0:
            logger.error(f"colmap image_undistorter failed with return code {returncode}")
            return False

        logger.info("Image undistortion completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error undistorting images: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Test - this will fail without proper setup
    print("COLMAP undistorter module loaded")

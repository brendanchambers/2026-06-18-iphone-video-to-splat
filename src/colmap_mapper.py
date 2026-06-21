"""
COLMAP sparse reconstruction (mapper) utility.
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional
from omegaconf import DictConfig


logger = logging.getLogger(__name__)


def sparse_reconstruction(
    database_path: Path,
    image_path: Path,
    output_path: Path,
    config: Optional[DictConfig] = None,
    log_file: Optional[Path] = None,
) -> bool:
    """
    Perform sparse reconstruction using COLMAP mapper.

    Args:
        database_path: Path to COLMAP database file
        image_path: Path to directory containing images
        output_path: Path to save sparse reconstruction
        config: Optional OmegaConf config object with COLMAP parameters
        log_file: Optional path to log file

    Returns:
        True if successful, False otherwise
    """
    database_path = Path(database_path)
    image_path = Path(image_path)
    output_path = Path(output_path)

    # Validate inputs
    if not database_path.exists():
        logger.error(f"Database file not found: {database_path}")
        return False

    if not image_path.exists():
        logger.error(f"Image directory not found: {image_path}")
        return False

    output_path.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"Performing sparse reconstruction")
        logger.info(f"Database: {database_path}")
        logger.info(f"Images: {image_path}")
        logger.info(f"Output: {output_path}")

        # Build command with COLMAP parameters
        cmd = [
            "colmap", "mapper",
            "--database_path", str(database_path),
            "--image_path", str(image_path),
            "--output_path", str(output_path),
        ]

        if config and "colmap" in config and "mapper" in config.colmap:
            mapper_config = config.colmap.mapper
            params = [
                ("--Mapper.multiple_models", mapper_config.multiple_models),
                ("--Mapper.max_num_models", mapper_config.max_num_models),
                ("--Mapper.min_model_size", mapper_config.min_model_size),
                ("--Mapper.init_num_trials", mapper_config.init_num_trials),
                ("--Mapper.extract_colors", mapper_config.extract_colors),
                ("--Mapper.num_threads", mapper_config.num_threads),
                ("--Mapper.min_focal_length_ratio", mapper_config.min_focal_length_ratio),
                ("--Mapper.max_focal_length_ratio", mapper_config.max_focal_length_ratio),
                ("--Mapper.ba_refine_focal_length", mapper_config.ba_refine_focal_length),
                ("--Mapper.ba_refine_principal_point", mapper_config.ba_refine_principal_point),
                ("--Mapper.ba_refine_extra_params", mapper_config.ba_refine_extra_params),
                ("--Mapper.ba_local_max_num_iterations", mapper_config.ba_local_max_num_iterations),
                ("--Mapper.ba_global_max_num_iterations", mapper_config.ba_global_max_num_iterations),
                ("--Mapper.ba_global_frames_freq", mapper_config.ba_global_frames_freq),
                ("--Mapper.ba_global_points_freq", mapper_config.ba_global_points_freq),
                ("--Mapper.filter_max_reproj_error", mapper_config.filter_max_reproj_error),
                ("--Mapper.filter_min_tri_angle", mapper_config.filter_min_tri_angle),
                ("--Mapper.init_max_error", mapper_config.init_max_error),
                ("--Mapper.init_min_tri_angle", mapper_config.init_min_tri_angle),
                ("--Mapper.abs_pose_max_error", mapper_config.abs_pose_max_error),
                ("--Mapper.abs_pose_min_num_inliers", mapper_config.abs_pose_min_num_inliers),
            ]
            for key, value in params:
                cmd.extend([key, str(value)])
        else:
            # Use defaults
            cmd.extend([
                "--Mapper.multiple_models", "1",
                "--Mapper.max_num_models", "50",
                "--Mapper.min_model_size", "10",
                "--Mapper.init_num_trials", "200",
                "--Mapper.extract_colors", "1",
                "--Mapper.num_threads", "-1",
                "--Mapper.min_focal_length_ratio", "0.1",
                "--Mapper.max_focal_length_ratio", "10",
                "--Mapper.ba_refine_focal_length", "1",
                "--Mapper.ba_refine_principal_point", "0",
                "--Mapper.ba_refine_extra_params", "1",
                "--Mapper.ba_local_max_num_iterations", "25",
                "--Mapper.ba_global_max_num_iterations", "50",
                "--Mapper.ba_global_frames_freq", "500",
                "--Mapper.ba_global_points_freq", "250000",
                "--Mapper.filter_max_reproj_error", "8",
                "--Mapper.filter_min_tri_angle", "1.5",
                "--Mapper.init_max_error", "4",
                "--Mapper.init_min_tri_angle", "16",
                "--Mapper.abs_pose_max_error", "12",
                "--Mapper.abs_pose_min_num_inliers", "30",
            ])

        logger.info(f"Running: colmap mapper")

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
            logger.error(f"colmap mapper failed with return code {returncode}")
            return False

        logger.info("Sparse reconstruction completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error in sparse reconstruction: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Test - this will fail without proper setup
    print("COLMAP mapper module loaded")

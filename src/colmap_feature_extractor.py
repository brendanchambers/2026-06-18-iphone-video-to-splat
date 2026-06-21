"""
COLMAP feature extraction utility.
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional
from omegaconf import DictConfig


logger = logging.getLogger(__name__)


def extract_features(
    database_path: Path,
    image_path: Path,
    config: Optional[DictConfig] = None,
    log_file: Optional[Path] = None,
) -> bool:
    """
    Extract SIFT features from images using COLMAP.

    Args:
        database_path: Path to COLMAP database file
        image_path: Path to directory containing images
        config: Optional OmegaConf config object with COLMAP parameters
        log_file: Optional path to log file

    Returns:
        True if successful, False otherwise
    """
    database_path = Path(database_path)
    image_path = Path(image_path)

    # Validate inputs
    if not image_path.exists():
        logger.error(f"Image directory not found: {image_path}")
        return False

    try:
        logger.info(f"Extracting features from images: {image_path}")
        logger.info(f"Database: {database_path}")

        # Build command with COLMAP parameters
        cmd = ["colmap", "feature_extractor", "--database_path", str(database_path), "--image_path", str(image_path)]

        if config and "colmap" in config and "feature_extraction" in config.colmap:
            feat_config = config.colmap.feature_extraction
            params = [
                ("--ImageReader.camera_model", feat_config.camera_model),
                ("--ImageReader.single_camera", feat_config.single_camera),
                ("--ImageReader.default_focal_length_factor", feat_config.default_focal_length_factor),
                ("--FeatureExtraction.type", feat_config.type),
                ("--FeatureExtraction.use_gpu", feat_config.use_gpu),
                ("--FeatureExtraction.gpu_index", feat_config.gpu_index),
                ("--SiftExtraction.max_num_features", feat_config.sift_max_num_features),
                ("--SiftExtraction.first_octave", feat_config.sift_first_octave),
                ("--SiftExtraction.num_octaves", feat_config.sift_num_octaves),
                ("--SiftExtraction.octave_resolution", feat_config.sift_octave_resolution),
                ("--SiftExtraction.peak_threshold", feat_config.sift_peak_threshold),
                ("--SiftExtraction.edge_threshold", feat_config.sift_edge_threshold),
                ("--SiftExtraction.estimate_affine_shape", feat_config.sift_estimate_affine_shape),
                ("--SiftExtraction.max_num_orientations", feat_config.sift_max_num_orientations),
                ("--SiftExtraction.upright", feat_config.sift_upright),
            ]
            for key, value in params:
                cmd.extend([key, str(value)])
        else:
            # Use defaults
            cmd.extend([
                "--ImageReader.camera_model", "RADIAL",
                "--ImageReader.single_camera", "1",
                "--ImageReader.default_focal_length_factor", "1.2",
                "--FeatureExtraction.type", "SIFT",
                "--FeatureExtraction.use_gpu", "1",
                "--FeatureExtraction.gpu_index", "-1",
                "--SiftExtraction.max_num_features", "4096",
                "--SiftExtraction.first_octave", "-1",
                "--SiftExtraction.num_octaves", "4",
                "--SiftExtraction.octave_resolution", "3",
                "--SiftExtraction.peak_threshold", "0.00667",
                "--SiftExtraction.edge_threshold", "20",
                "--SiftExtraction.estimate_affine_shape", "0",
                "--SiftExtraction.max_num_orientations", "2",
                "--SiftExtraction.upright", "0",
            ])

        logger.info(f"Running: colmap feature_extractor")

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
            logger.error(f"colmap feature_extractor failed with return code {returncode}")
            return False

        logger.info("Feature extraction completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error extracting features: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Test - this will fail without proper setup
    print("COLMAP feature extractor module loaded")

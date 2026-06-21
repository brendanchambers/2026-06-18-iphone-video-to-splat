"""
COLMAP feature matching utility.
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional
from omegaconf import DictConfig


logger = logging.getLogger(__name__)


def match_features(
    database_path: Path,
    config: Optional[DictConfig] = None,
    log_file: Optional[Path] = None,
) -> bool:
    """
    Match SIFT features using COLMAP's sequential matcher.

    Args:
        database_path: Path to COLMAP database file
        config: Optional OmegaConf config object with COLMAP parameters
        log_file: Optional path to log file

    Returns:
        True if successful, False otherwise
    """
    database_path = Path(database_path)

    # Validate inputs
    if not database_path.exists():
        logger.error(f"Database file not found: {database_path}")
        return False

    try:
        logger.info(f"Matching features in database: {database_path}")

        # Build command with COLMAP parameters
        cmd = ["colmap", "sequential_matcher", "--database_path", str(database_path)]

        if config and "colmap" in config and "feature_matching" in config.colmap:
            match_config = config.colmap.feature_matching
            params = [
                ("--FeatureMatching.type", match_config.type),
                ("--FeatureMatching.use_gpu", match_config.use_gpu),
                ("--FeatureMatching.gpu_index", match_config.gpu_index),
                ("--FeatureMatching.guided_matching", match_config.guided_matching),
                ("--FeatureMatching.skip_geometric_verification", match_config.skip_geometric_verification),
                ("--FeatureMatching.max_num_matches", match_config.max_num_matches),
                ("--SiftMatching.max_ratio", match_config.sift_max_ratio),
                ("--SiftMatching.max_distance", match_config.sift_max_distance),
                ("--SiftMatching.cross_check", match_config.sift_cross_check),
                ("--SiftMatching.cpu_brute_force_matcher", match_config.cpu_brute_force_matcher),
                ("--TwoViewGeometry.min_num_inliers", match_config.two_view_min_num_inliers),
                ("--TwoViewGeometry.max_error", match_config.two_view_max_error),
                ("--TwoViewGeometry.confidence", match_config.two_view_confidence),
                ("--TwoViewGeometry.max_num_trials", match_config.two_view_max_num_trials),
                ("--TwoViewGeometry.min_inlier_ratio", match_config.two_view_min_inlier_ratio),
                ("--SequentialMatching.overlap", match_config.sequential_overlap),
            ]
            for key, value in params:
                cmd.extend([key, str(value)])
        else:
            # Use defaults
            cmd.extend([
                "--FeatureMatching.type", "SIFT_BRUTEFORCE",
                "--FeatureMatching.use_gpu", "1",
                "--FeatureMatching.gpu_index", "-1",
                "--FeatureMatching.guided_matching", "0",
                "--FeatureMatching.skip_geometric_verification", "0",
                "--FeatureMatching.max_num_matches", "32768",
                "--SiftMatching.max_ratio", "0.8",
                "--SiftMatching.max_distance", "0.7",
                "--SiftMatching.cross_check", "1",
                "--SiftMatching.cpu_brute_force_matcher", "0",
                "--TwoViewGeometry.min_num_inliers", "15",
                "--TwoViewGeometry.max_error", "4",
                "--TwoViewGeometry.confidence", "0.999",
                "--TwoViewGeometry.max_num_trials", "10000",
                "--TwoViewGeometry.min_inlier_ratio", "0.25",
                "--SequentialMatching.overlap", "20",
            ])

        logger.info(f"Running: colmap sequential_matcher")

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
            logger.error(f"colmap sequential_matcher failed with return code {returncode}")
            return False

        logger.info("Feature matching completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error matching features: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Test - this will fail without proper setup
    print("COLMAP feature matcher module loaded")

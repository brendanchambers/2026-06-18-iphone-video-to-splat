"""
Main pipeline orchestrator for 3D Gaussian Splat training from video.
Uses Hydra + OmegaConf for configuration management.
"""
import logging
from pathlib import Path
from typing import Optional
import hydra
from omegaconf import DictConfig

from src.frame_extractor import extract_frames
from src.colmap_feature_extractor import extract_features
from src.colmap_feature_matcher import match_features
from src.colmap_mapper import sparse_reconstruction
from src.colmap_undistorter import undistort_images
from src.opensplat_trainer import train_splat


logger = logging.getLogger(__name__)


def setup_logging(log_dir: Path) -> None:
    """Configure logging for the pipeline."""
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create file handler
    log_file = log_dir / "pipeline.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


class Pipeline:
    """Orchestrates the complete Gaussian Splat training pipeline."""

    def __init__(self, config: DictConfig):
        """
        Initialize the pipeline with configuration.

        Args:
            config: OmegaConf configuration object
        """
        self.config = config
        self.project_dir = Path(config.project.dir)
        self.log_dir = Path(config.paths.log_dir)
        self.colmap_log_file = self.log_dir / "colmap_pipeline.log"
        self.opensplat_log_file = self.log_dir / "opensplat_pipeline.log"

        # Create output directories
        Path(config.paths.images_dir).mkdir(parents=True, exist_ok=True)
        Path(config.paths.sparse_dir).mkdir(parents=True, exist_ok=True)
        Path(config.paths.distortion_corrected_dir).mkdir(parents=True, exist_ok=True)
        Path(config.paths.opensplat_output_dir).mkdir(parents=True, exist_ok=True)
        Path(config.paths.val_render_dir).mkdir(parents=True, exist_ok=True)

        setup_logging(self.log_dir)

    def run_frame_extraction(self) -> bool:
        """Extract frames from video."""
        logger.info("=" * 60)
        logger.info("STEP 1: Frame Extraction")
        logger.info("=" * 60)

        video_path = self.project_dir / self.config.project.video_path
        output_dir = Path(self.config.paths.images_dir)

        success = extract_frames(
            video_path=video_path,
            output_dir=output_dir,
            fps=self.config.frame_extraction.fps,
            quality=self.config.frame_extraction.quality,
            config=self.config,
            log_file=self.colmap_log_file,
        )

        if success:
            logger.info("✓ Frame extraction completed")
        else:
            logger.error("✗ Frame extraction failed")

        return success

    def run_feature_extraction(self) -> bool:
        """Extract SIFT features from frames."""
        logger.info("=" * 60)
        logger.info("STEP 2: Feature Extraction")
        logger.info("=" * 60)

        database_path = Path(self.config.paths.database_path)
        image_path = Path(self.config.paths.images_dir)

        success = extract_features(
            database_path=database_path,
            image_path=image_path,
            config=self.config,
            log_file=self.colmap_log_file,
        )

        if success:
            logger.info("✓ Feature extraction completed")
        else:
            logger.error("✗ Feature extraction failed")

        return success

    def run_feature_matching(self) -> bool:
        """Match features between frames."""
        logger.info("=" * 60)
        logger.info("STEP 3: Feature Matching")
        logger.info("=" * 60)

        database_path = Path(self.config.paths.database_path)

        success = match_features(
            database_path=database_path,
            config=self.config,
            log_file=self.colmap_log_file,
        )

        if success:
            logger.info("✓ Feature matching completed")
        else:
            logger.error("✗ Feature matching failed")

        return success

    def run_sparse_reconstruction(self) -> bool:
        """Compute sparse 3D reconstruction."""
        logger.info("=" * 60)
        logger.info("STEP 4: Sparse Reconstruction")
        logger.info("=" * 60)

        database_path = Path(self.config.paths.database_path)
        image_path = Path(self.config.paths.images_dir)
        output_path = Path(self.config.paths.sparse_dir)

        success = sparse_reconstruction(
            database_path=database_path,
            image_path=image_path,
            output_path=output_path,
            config=self.config,
            log_file=self.colmap_log_file,
        )

        if success:
            logger.info("✓ Sparse reconstruction completed")
        else:
            logger.error("✗ Sparse reconstruction failed")

        return success

    def run_undistortion(self) -> bool:
        """Undistort images and correct camera poses."""
        logger.info("=" * 60)
        logger.info("STEP 5: Image Undistortion")
        logger.info("=" * 60)

        image_path = Path(self.config.paths.images_dir)
        input_model_path = Path(self.config.paths.sparse_dir) / "0"
        output_path = Path(self.config.paths.distortion_corrected_dir)

        success = undistort_images(
            image_path=image_path,
            input_model_path=input_model_path,
            output_path=output_path,
            config=self.config,
            log_file=self.colmap_log_file,
        )

        if success:
            logger.info("✓ Image undistortion completed")
        else:
            logger.error("✗ Image undistortion failed")

        return success

    def run_splat_training(self) -> bool:
        """Train 3D Gaussian Splat."""
        logger.info("=" * 60)
        logger.info("STEP 6: OpenSplat Training")
        logger.info("=" * 60)

        sparse_model_path = Path(self.config.paths.distortion_corrected_dir) / "sparse"
        images_path = Path(self.config.paths.distortion_corrected_dir) / "images"
        output_dir = Path(self.config.paths.opensplat_output_dir)
        opensplat_bin = Path(self.config.paths.opensplat_bin)

        success = train_splat(
            sparse_model_path=sparse_model_path,
            images_path=images_path,
            output_dir=output_dir,
            opensplat_bin=opensplat_bin,
            experiment_name=self.config.project.experiment_name,
            config=self.config,
            log_file=self.opensplat_log_file,
        )

        if success:
            logger.info("✓ Splat training completed")
        else:
            logger.error("✗ Splat training failed")

        return success

    def run_full_pipeline(self, skip_steps: Optional[list] = None) -> bool:
        """
        Run the complete pipeline.

        Args:
            skip_steps: Optional list of step names to skip (e.g., ["frame_extraction"])

        Returns:
            True if all steps succeed, False otherwise
        """
        skip_steps = skip_steps or []

        logger.info("")
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║" + " " * 10 + "3D Gaussian Splat Training Pipeline" + " " * 14 + "║")
        logger.info("╚" + "=" * 58 + "╝")
        logger.info(f"Experiment: {self.config.project.experiment_name}")
        logger.info(f"Project dir: {self.project_dir}")
        logger.info("")

        steps = [
            ("frame_extraction", self.run_frame_extraction),
            ("feature_extraction", self.run_feature_extraction),
            ("feature_matching", self.run_feature_matching),
            ("sparse_reconstruction", self.run_sparse_reconstruction),
            ("undistortion", self.run_undistortion),
            ("splat_training", self.run_splat_training),
        ]

        all_success = True
        for step_name, step_func in steps:
            if step_name in skip_steps:
                logger.info(f"SKIPPING: {step_name}")
                continue

            try:
                success = step_func()
                if not success:
                    all_success = False
                    logger.error(f"Pipeline failed at step: {step_name}")
                    return False
            except Exception as e:
                logger.error(f"Exception in {step_name}: {e}", exc_info=True)
                all_success = False
                return False

        if all_success:
            logger.info("")
            logger.info("╔" + "=" * 58 + "╗")
            logger.info("║" + " " * 20 + "Pipeline Complete!" + " " * 20 + "║")
            logger.info("╚" + "=" * 58 + "╝")
            logger.info(f"Output PLY: {self.config.paths.opensplat_output_dir}")

        return all_success


@hydra.main(version_base=None, config_path="config", config_name="baseline")
def main(config: DictConfig) -> None:
    """Main entry point with Hydra configuration."""
    pipeline = Pipeline(config)
    success = pipeline.run_full_pipeline()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()

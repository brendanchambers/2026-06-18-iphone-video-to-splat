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
from src.timing_recorder import TimingRecorder
from src.experiment_tracker import (
    extract_final_loss_value,
    extract_validation_loss,
    extract_total_running_time,
    log_experiment_result,
)
from scripts.analyze_training_loss import load_loss_records, analyze_loss, print_analysis, plot_loss


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
        self.timing_recorder = TimingRecorder()

        # Create output directories
        Path(config.paths.colmap_sfm_camera_model).mkdir(parents=True, exist_ok=True)
        Path(config.paths.colmap_sfm_linearized).mkdir(parents=True, exist_ok=True)
        Path(config.paths.images_dir).mkdir(parents=True, exist_ok=True)
        Path(config.paths.sparse_dir).mkdir(parents=True, exist_ok=True)
        Path(config.paths.opensplat_output_dir).mkdir(parents=True, exist_ok=True)

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
        output_path = Path(self.config.paths.colmap_sfm_linearized)

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

        sparse_model_path = Path(self.config.paths.colmap_sfm_linearized) / "sparse"
        images_path = Path(self.config.paths.colmap_sfm_linearized) / "images"
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
            # Analyze training loss
            self.analyze_training_loss(output_dir)
        else:
            logger.error("✗ Splat training failed")

        return success

    def analyze_training_loss(self, output_dir: Path) -> None:
        """
        Analyze and visualize training loss from JSONL log file.

        Args:
            output_dir: Directory containing the JSONL loss file
        """
        logger.info("=" * 60)
        logger.info("Analyzing Training Loss")
        logger.info("=" * 60)

        # Find the most recent training loss JSONL file (train_*.jsonl, not val_*.jsonl)
        jsonl_files = sorted(output_dir.glob("train_*.jsonl"))
        if not jsonl_files:
            logger.warning("No training loss log file found")
            return

        jsonl_file = jsonl_files[-1]  # Get the most recent file
        records = load_loss_records(jsonl_file)

        if not records:
            logger.warning(f"No loss records found in {jsonl_file.name}")
            return

        # Print analysis
        print_analysis(jsonl_file, records)

        # Generate plot
        try:
            plot_loss(records, jsonl_file)
        except Exception as e:
            logger.warning(f"Could not generate plot: {e}")

    def log_experiment_results(self, output_dir: Path) -> bool:
        """
        Log experiment results to the experiment group JSONL file.

        Extracts final training loss, validation loss, and total running time,
        then appends a record to reports/experiments/<experiment_group>.jsonl

        Args:
            output_dir: Directory containing timing and loss JSONL files

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info("Logging Experiment Results")
        logger.info("=" * 60)

        output_dir = Path(output_dir)
        experiment_name = self.config.project.experiment_name
        experiment_group = self.config.project.experiment_group

        # Find the most recent timing file
        timing_files = sorted(output_dir.glob("running-time_*.jsonl"))
        if not timing_files:
            logger.warning("No timing log file found")
            return False

        timing_file = timing_files[-1]

        # Find the most recent training loss file
        train_loss_files = sorted(output_dir.glob("train_*.jsonl"))
        if not train_loss_files:
            logger.warning("No training loss log file found")
            return False

        train_loss_file = train_loss_files[-1]

        # Try to find validation loss file (optional)
        val_loss_files = sorted(output_dir.glob("val_*.jsonl"))
        val_loss_file = val_loss_files[-1] if val_loss_files else None

        # Extract values
        total_running_time = extract_total_running_time(timing_file)
        train_loss = extract_final_loss_value(train_loss_file)
        val_loss = extract_validation_loss(val_loss_file) if val_loss_file else None

        if total_running_time is None or train_loss is None:
            logger.error("Failed to extract required metrics from log files")
            return False

        # Log to experiment group file
        experiment_output = (
            Path(self.config.paths.log_dir).parent
            / "reports"
            / "experiments"
            / f"{experiment_group}.jsonl"
        )

        success = log_experiment_result(
            experiment_name=experiment_name,
            experiment_group=experiment_group,
            total_running_time=total_running_time,
            train_loss=train_loss,
            val_loss=val_loss,
            output_jsonl_path=experiment_output,
        )

        if success:
            logger.info(f"Experiment results logged to: {experiment_output}")
            logger.info(f"  Experiment: {experiment_name}")
            logger.info(f"  Group: {experiment_group}")
            logger.info(f"  Train loss: {train_loss:.6f}")
            if val_loss is not None:
                logger.info(f"  Validation loss: {val_loss:.6f}")
            logger.info(f"  Total time: {total_running_time:.2f}s ({total_running_time/60:.2f}m)")
        else:
            logger.error("Failed to log experiment results")

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
                self.timing_recorder.start_step(step_name)
                success = step_func()
                self.timing_recorder.end_step(step_name, success=success)

                if not success:
                    all_success = False
                    logger.error(f"Pipeline failed at step: {step_name}")
                    return False
            except Exception as e:
                self.timing_recorder.end_step(step_name, success=False)
                logger.error(f"Exception in {step_name}: {e}", exc_info=True)
                all_success = False
                return False

        if all_success:
            logger.info("")
            logger.info("╔" + "=" * 58 + "╗")
            logger.info("║" + " " * 20 + "Pipeline Complete!" + " " * 20 + "║")
            logger.info("╚" + "=" * 58 + "╝")
            logger.info(f"Output directory: {self.config.paths.opensplat_output_dir}")
            logger.info(f"  - PLY file: *.ply (3D Gaussian Splat)")
            logger.info(f"  - Loss log: *.jsonl (Training loss per step)")
            logger.info(f"  - Timing log: running-time_*.jsonl (Step execution times)")

            # Print timing summary and save to file
            self.timing_recorder.print_summary()
            self.timing_recorder.save_to_jsonl(Path(self.config.paths.opensplat_output_dir))

            # Log experiment results to group file
            self.log_experiment_results(Path(self.config.paths.opensplat_output_dir))

        return all_success


@hydra.main(version_base=None, config_path="config", config_name="baseline")
def main(config: DictConfig) -> None:
    """Main entry point with Hydra configuration."""
    pipeline = Pipeline(config)
    pipeline.run_full_pipeline()


if __name__ == "__main__":
    main()

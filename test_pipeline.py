#!/usr/bin/env python3
"""
Test script to validate the Python pipeline setup.
This script tests each component individually without running heavy computations.
"""
import sys
from pathlib import Path
from omegaconf import OmegaConf
import logging

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline import Pipeline
from src.frame_extractor import extract_frames
from src.colmap_feature_extractor import extract_features
from src.colmap_feature_matcher import match_features
from src.colmap_mapper import sparse_reconstruction
from src.colmap_undistorter import undistort_images
from src.opensplat_trainer import train_splat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def test_config_loading():
    """Test that configuration loads correctly."""
    logger.info("=" * 60)
    logger.info("TEST 1: Configuration Loading")
    logger.info("=" * 60)

    config = OmegaConf.load("config/config.yaml")
    OmegaConf.resolve(config)

    assert config.project.experiment_name == "testing"
    assert "images_dir" in config.paths
    assert "opensplat_bin" in config.paths
    assert config.opensplat.num_iters == 1500

    logger.info("✓ Config loaded successfully")
    logger.info(f"  Experiment: {config.project.experiment_name}")
    logger.info(f"  Frames per second: {config.frame_extraction.fps}")
    logger.info(f"  OpenSplat iterations: {config.opensplat.num_iters}")
    logger.info(f"  Validation enabled: {config.validation.enabled}")
    return config


def test_pipeline_instantiation(config):
    """Test that pipeline can be instantiated."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 2: Pipeline Instantiation")
    logger.info("=" * 60)

    pipeline = Pipeline(config)

    assert pipeline.project_dir.exists()
    assert pipeline.config is not None

    logger.info("✓ Pipeline instantiated successfully")
    logger.info(f"  Project dir: {pipeline.project_dir}")
    logger.info(f"  Log dir: {pipeline.log_dir}")
    logger.info(f"  Colmap log: {pipeline.colmap_log_file}")
    logger.info(f"  OpenSplat log: {pipeline.opensplat_log_file}")
    return pipeline


def test_module_imports():
    """Test that all modules can be imported."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 3: Module Imports")
    logger.info("=" * 60)

    modules = [
        ("frame_extractor", extract_frames),
        ("colmap_feature_extractor", extract_features),
        ("colmap_feature_matcher", match_features),
        ("colmap_mapper", sparse_reconstruction),
        ("colmap_undistorter", undistort_images),
        ("opensplat_trainer", train_splat),
    ]

    for name, func in modules:
        assert callable(func)
        logger.info(f"✓ {name}: imported and callable")


def test_config_parameter_coverage(config):
    """Test that all important config parameters are present."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 4: Config Parameter Coverage")
    logger.info("=" * 60)

    # Frame extraction params
    assert hasattr(config.frame_extraction, "fps")
    assert hasattr(config.frame_extraction, "quality")
    logger.info("✓ Frame extraction parameters present")

    # COLMAP feature extraction params
    assert hasattr(config.colmap.feature_extraction, "sift_max_num_features")
    logger.info("✓ Feature extraction parameters present")

    # COLMAP matching params
    assert hasattr(config.colmap.feature_matching, "sequential_overlap")
    logger.info("✓ Feature matching parameters present")

    # COLMAP mapper params
    assert hasattr(config.colmap.mapper, "filter_max_reproj_error")
    logger.info("✓ Mapper parameters present")

    # COLMAP undistorter params
    assert hasattr(config.colmap.undistorter, "output_type")
    logger.info("✓ Undistorter parameters present")

    # OpenSplat params
    assert hasattr(config.opensplat, "num_iters")
    assert hasattr(config.opensplat, "ssim_weight")
    logger.info("✓ OpenSplat parameters present")

    # Validation params
    assert hasattr(config.validation, "enabled")
    assert hasattr(config.validation, "image")
    logger.info("✓ Validation parameters present")


def test_pipeline_methods(pipeline):
    """Test that pipeline has all required methods."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 5: Pipeline Methods")
    logger.info("=" * 60)

    methods = [
        "run_frame_extraction",
        "run_feature_extraction",
        "run_feature_matching",
        "run_sparse_reconstruction",
        "run_undistortion",
        "run_splat_training",
        "run_full_pipeline",
    ]

    for method_name in methods:
        assert hasattr(pipeline, method_name)
        assert callable(getattr(pipeline, method_name))
        logger.info(f"✓ Pipeline.{method_name}() exists and callable")


def test_directory_structure(pipeline):
    """Test that required directories are created."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 6: Directory Structure")
    logger.info("=" * 60)

    dirs = [
        ("images", Path(pipeline.config.paths.images_dir)),
        ("sparse", Path(pipeline.config.paths.sparse_dir)),
        ("distortion_corrected", Path(pipeline.config.paths.distortion_corrected_dir)),
        ("opensplat_output", Path(pipeline.config.paths.opensplat_output_dir)),
        ("logs", pipeline.log_dir),
        ("validation_renders", Path(pipeline.config.paths.val_render_dir)),
    ]

    for dir_name, dir_path in dirs:
        assert dir_path.exists(), f"Directory {dir_name} not created"
        logger.info(f"✓ {dir_name}: {dir_path}")


def main():
    """Run all tests."""
    logger.info("")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 14 + "Python Pipeline Test Suite" + " " * 18 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("")

    try:
        # Run tests
        config = test_config_loading()
        pipeline = test_pipeline_instantiation(config)
        test_module_imports()
        test_config_parameter_coverage(config)
        test_pipeline_methods(pipeline)
        test_directory_structure(pipeline)

        # Summary
        logger.info("")
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║" + " " * 22 + "All Tests Passed!" + " " * 20 + "║")
        logger.info("╚" + "=" * 58 + "╝")
        logger.info("")
        logger.info("Pipeline is ready to use!")
        logger.info("Run with: uv run python pipeline.py")
        logger.info("")

        return 0

    except Exception as e:
        logger.error("")
        logger.error("╔" + "=" * 58 + "╗")
        logger.error("║" + " " * 22 + "Test Failed!" + " " * 24 + "║")
        logger.error("╚" + "=" * 58 + "╝")
        logger.error(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

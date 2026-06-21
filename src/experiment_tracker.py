"""
Experiment tracking utility for logging experiment results to JSONL files.
Records final training loss, validation loss, and total running time for each experiment.
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass, asdict
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class ExperimentResult:
    """Record of a single experiment's results."""
    experiment_name: str
    experiment_group: str
    timestamp: str  # ISO format timestamp
    total_running_time: float  # seconds
    train_loss: float
    val_loss: Optional[float] = None


def extract_final_loss_value(jsonl_path: Path) -> Optional[float]:
    """
    Extract the final loss value from a training loss JSONL file.

    Args:
        jsonl_path: Path to training loss JSONL file (e.g., train_YYYYMMDD_HHMM.jsonl)

    Returns:
        Final loss value (float) or None if file not found or empty
    """
    if not jsonl_path.exists():
        logger.warning(f"Training loss file not found: {jsonl_path}")
        return None

    try:
        with open(jsonl_path, "r") as f:
            lines = f.readlines()
            if not lines:
                logger.warning(f"Training loss file is empty: {jsonl_path}")
                return None

            # Get the last line
            last_line = lines[-1].strip()
            if not last_line:
                logger.warning(f"Last line of training loss file is empty: {jsonl_path}")
                return None

            record = json.loads(last_line)
            # Loss records have format: {"step": N, "loss": X, "timestamp": "..."}
            if "loss" in record:
                return float(record["loss"])
            else:
                logger.warning(f"No 'loss' field in last record: {jsonl_path}")
                return None

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error parsing training loss file {jsonl_path}: {e}")
        return None


def extract_validation_loss(jsonl_path: Path) -> Optional[float]:
    """
    Extract the final validation loss value from a validation loss JSONL file.

    Args:
        jsonl_path: Path to validation loss JSONL file (e.g., val_YYYYMMDD_HHMM.jsonl)

    Returns:
        Final validation loss value (float) or None if file not found or empty
    """
    if not jsonl_path.exists():
        logger.debug(f"Validation loss file not found: {jsonl_path}")
        return None

    try:
        with open(jsonl_path, "r") as f:
            lines = f.readlines()
            if not lines:
                logger.debug(f"Validation loss file is empty: {jsonl_path}")
                return None

            # Get the last line
            last_line = lines[-1].strip()
            if not last_line:
                logger.debug(f"Last line of validation loss file is empty: {jsonl_path}")
                return None

            record = json.loads(last_line)
            # Validation loss records have format: {"validation_loss": X, "timestamp": "..."}
            if "validation_loss" in record:
                return float(record["validation_loss"])
            else:
                logger.debug(f"No 'validation_loss' field in last record: {jsonl_path}")
                return None

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error parsing validation loss file {jsonl_path}: {e}")
        return None


def extract_total_running_time(timing_jsonl_path: Path) -> Optional[float]:
    """
    Extract the total running time from a timing JSONL file.

    Args:
        timing_jsonl_path: Path to timing JSONL file (e.g., running-time_YYYYMMDD_HHMM.jsonl)

    Returns:
        Total running time in seconds (float) or None if file not found or empty
    """
    if not timing_jsonl_path.exists():
        logger.warning(f"Timing file not found: {timing_jsonl_path}")
        return None

    try:
        with open(timing_jsonl_path, "r") as f:
            lines = f.readlines()
            if not lines:
                logger.warning(f"Timing file is empty: {timing_jsonl_path}")
                return None

            # Get the last line which contains the total_time summary
            last_line = lines[-1].strip()
            if not last_line:
                logger.warning(f"Last line of timing file is empty: {timing_jsonl_path}")
                return None

            record = json.loads(last_line)
            # Summary record has format: {"total_time": X, "timestamp": "..."}
            if "total_time" in record:
                return float(record["total_time"])
            else:
                logger.warning(f"No 'total_time' field in summary record: {timing_jsonl_path}")
                return None

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error parsing timing file {timing_jsonl_path}: {e}")
        return None


def log_experiment_result(
    experiment_name: str,
    experiment_group: str,
    total_running_time: float,
    train_loss: float,
    val_loss: Optional[float],
    output_jsonl_path: Path,
) -> bool:
    """
    Log experiment result to a group JSONL file.

    Appends a new experiment record to the group JSONL file. Creates the file if it doesn't exist.

    Args:
        experiment_name: Name of the experiment
        experiment_group: Group name for organizing related experiments
        total_running_time: Total pipeline execution time in seconds
        train_loss: Final training loss value
        val_loss: Final validation loss value (or None if validation disabled)
        output_jsonl_path: Path to the experiment group JSONL file (e.g., reports/experiments/baseline.jsonl)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure output directory exists
        output_jsonl_path.parent.mkdir(parents=True, exist_ok=True)

        # Create the experiment result record
        result = ExperimentResult(
            experiment_name=experiment_name,
            experiment_group=experiment_group,
            timestamp=datetime.now().isoformat(),
            total_running_time=total_running_time,
            train_loss=train_loss,
            val_loss=val_loss,
        )

        # Append to JSONL file
        with open(output_jsonl_path, "a") as f:
            f.write(json.dumps(asdict(result)) + "\n")

        logger.info(f"Logged experiment to: {output_jsonl_path}")
        return True

    except Exception as e:
        logger.error(f"Error logging experiment result: {e}")
        return False


if __name__ == "__main__":
    # Test the utility functions
    logging.basicConfig(level=logging.INFO)

    # Example usage
    test_dir = Path("/tmp/test_experiment")
    test_dir.mkdir(exist_ok=True)

    # Create test files
    train_loss_file = test_dir / "train_20260621_1436.jsonl"
    val_loss_file = test_dir / "val_20260621_1436.jsonl"
    timing_file = test_dir / "running-time_20260621_1436.jsonl"

    # Write test data
    with open(train_loss_file, "w") as f:
        f.write('{"step": 0, "loss": 1.5, "timestamp": "2026-06-21T14:30:00"}\n')
        f.write('{"step": 100, "loss": 0.8, "timestamp": "2026-06-21T14:30:10"}\n')
        f.write('{"step": 200, "loss": 0.45, "timestamp": "2026-06-21T14:30:20"}\n')

    with open(val_loss_file, "w") as f:
        f.write('{"step": 0, "loss": 1.6, "timestamp": "2026-06-21T14:30:00"}\n')
        f.write('{"step": 100, "loss": 0.85, "timestamp": "2026-06-21T14:30:10"}\n')
        f.write('{"step": 200, "loss": 0.5, "timestamp": "2026-06-21T14:30:20"}\n')

    with open(timing_file, "w") as f:
        f.write('{"step": "frame_extraction", "elapsed_seconds": 100, "success": true}\n')
        f.write('{"step": "feature_extraction", "elapsed_seconds": 150, "success": true}\n')
        f.write('{"total_time": 500, "timestamp": "2026-06-21T14:42:20"}\n')

    # Test extraction functions
    train_loss = extract_final_loss_value(train_loss_file)
    val_loss = extract_validation_loss(val_loss_file)
    total_time = extract_total_running_time(timing_file)

    print(f"Extracted train loss: {train_loss}")
    print(f"Extracted val loss: {val_loss}")
    print(f"Extracted total time: {total_time}")

    # Test logging
    output_file = test_dir / "experiment_group.jsonl"
    success = log_experiment_result(
        experiment_name="test_exp",
        experiment_group="baseline",
        total_running_time=total_time,
        train_loss=train_loss,
        val_loss=val_loss,
        output_jsonl_path=output_file,
    )

    print(f"\nExperiment logged successfully: {success}")
    print(f"Output file: {output_file}")

    if output_file.exists():
        print("\nOutput file contents:")
        with open(output_file) as f:
            for line in f:
                print(line.rstrip())

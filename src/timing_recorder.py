"""
Timing recorder utility for measuring and logging pipeline step execution times.
Records elapsed time for each pipeline step to a JSONL file.
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import time


logger = logging.getLogger(__name__)


@dataclass
class TimingRecord:
    """Record of a single pipeline step execution time."""
    step: str
    start_time: str  # ISO format timestamp
    end_time: str    # ISO format timestamp
    elapsed_seconds: float
    success: bool


class TimingRecorder:
    """Records execution times for pipeline steps."""

    def __init__(self):
        """Initialize the timing recorder."""
        self.records: List[TimingRecord] = []
        self.step_start_times: Dict[str, float] = {}

    def start_step(self, step_name: str) -> None:
        """
        Mark the start of a pipeline step.

        Args:
            step_name: Name of the step being timed
        """
        self.step_start_times[step_name] = time.time()
        logger.info(f"[TIMING] Starting: {step_name}")

    def end_step(self, step_name: str, success: bool = True) -> None:
        """
        Mark the end of a pipeline step and record the timing.

        Args:
            step_name: Name of the step being timed
            success: Whether the step succeeded
        """
        if step_name not in self.step_start_times:
            logger.warning(f"[TIMING] No start time recorded for {step_name}")
            return

        end_time_unix = time.time()
        start_time_unix = self.step_start_times[step_name]
        elapsed = end_time_unix - start_time_unix

        # Convert to datetime for ISO format
        start_dt = datetime.fromtimestamp(start_time_unix)
        end_dt = datetime.fromtimestamp(end_time_unix)

        record = TimingRecord(
            step=step_name,
            start_time=start_dt.isoformat(),
            end_time=end_dt.isoformat(),
            elapsed_seconds=elapsed,
            success=success,
        )
        self.records.append(record)

        status = "✓" if success else "✗"
        logger.info(f"[TIMING] {status} Completed: {step_name} ({elapsed:.2f}s)")

        # Clean up
        del self.step_start_times[step_name]

    def save_to_jsonl(self, output_dir: Path) -> Path:
        """
        Save timing records to a JSONL file in the output directory.

        Includes a 'total_time' summary record at the end with the sum of all step times.

        Args:
            output_dir: Directory to save the timing file

        Returns:
            Path to the saved JSONL file
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"running-time_{timestamp}.jsonl"
        filepath = output_dir / filename

        # Calculate total elapsed time
        total_elapsed = sum(r.elapsed_seconds for r in self.records)

        # Write records to JSONL
        with open(filepath, "w") as f:
            for record in self.records:
                json.dumps(asdict(record))  # Validate it's serializable
                f.write(json.dumps(asdict(record)) + "\n")

            # Write total_time summary at the end
            total_record = {
                "total_time": total_elapsed,
                "timestamp": datetime.now().isoformat(),
            }
            f.write(json.dumps(total_record) + "\n")

        logger.info(f"[TIMING] Saved timing report to: {filepath}")
        return filepath

    def print_summary(self) -> None:
        """Print a summary of all recorded timings."""
        if not self.records:
            logger.info("[TIMING] No timing records available")
            return

        logger.info("")
        logger.info("=" * 70)
        logger.info("PIPELINE EXECUTION TIMING SUMMARY")
        logger.info("=" * 70)

        total_elapsed = sum(r.elapsed_seconds for r in self.records)

        for record in self.records:
            status = "✓" if record.success else "✗"
            pct = (record.elapsed_seconds / total_elapsed * 100) if total_elapsed > 0 else 0
            logger.info(f"{status} {record.step:<25} {record.elapsed_seconds:>8.2f}s  ({pct:>5.1f}%)")

        logger.info("-" * 70)
        logger.info(f"{'TOTAL':<27} {total_elapsed:>8.2f}s  (100.0%)")
        logger.info("=" * 70)
        logger.info("")


if __name__ == "__main__":
    # Test the timing recorder
    logging.basicConfig(level=logging.INFO)

    recorder = TimingRecorder()

    # Simulate some steps
    for step_name in ["frame_extraction", "feature_extraction", "feature_matching"]:
        recorder.start_step(step_name)
        time.sleep(0.1)  # Simulate work
        recorder.end_step(step_name, success=True)

    # Save and print summary
    recorder.print_summary()
    output_path = recorder.save_to_jsonl(Path("/tmp"))
    print(f"Saved to: {output_path}")

    # Show file contents
    with open(output_path) as f:
        for line in f:
            print(line.rstrip())

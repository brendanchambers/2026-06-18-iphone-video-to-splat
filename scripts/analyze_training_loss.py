#!/usr/bin/env python3
"""
Analyze and visualize training loss from JSONL log files.

Usage:
    # Analyze a single loss file (creates plot automatically)
    uv run python scripts/analyze_training_loss.py logs/current_scene_202606_1234.jsonl

    # Analyze all loss files in a directory (creates plots for each)
    uv run python scripts/analyze_training_loss.py data/intermediates/current_scene/splats/

    # Analyze without creating plot
    uv run python scripts/analyze_training_loss.py --no-plot logs/current_scene_202606_1234.jsonl
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import argparse


def load_loss_records(file_path: Path) -> List[Dict]:
    """Load JSONL loss records from file."""
    records = []
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return records

    try:
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON in {file_path}: {e}")
        return []

    return records


def analyze_loss(records: List[Dict]) -> Dict:
    """Calculate statistics from loss records."""
    if not records:
        return {}

    losses = [r["loss"] for r in records]
    steps = [r["step"] for r in records]

    return {
        "num_steps": len(records),
        "min_loss": min(losses),
        "max_loss": max(losses),
        "avg_loss": sum(losses) / len(losses),
        "final_loss": losses[-1],
        "first_step": min(steps),
        "last_step": max(steps),
    }


def print_analysis(file_path: Path, records: List[Dict]) -> None:
    """Print analysis results."""
    if not records:
        print(f"No loss records found in {file_path}")
        return

    stats = analyze_loss(records)

    print(f"\nTraining Loss Analysis: {file_path.name}")
    print("=" * 50)
    print(f"Total steps:     {stats['num_steps']}")
    print(f"Step range:      {stats['first_step']} → {stats['last_step']}")
    print(f"Min loss:        {stats['min_loss']:.6f}")
    print(f"Max loss:        {stats['max_loss']:.6f}")
    print(f"Average loss:    {stats['avg_loss']:.6f}")
    print(f"Final loss:      {stats['final_loss']:.6f}")
    print("=" * 50)


def load_validation_loss(jsonl_path: Path) -> float:
    """
    Load final validation loss from corresponding val_*.jsonl file.

    Args:
        jsonl_path: Path to training loss JSONL file (e.g., train_YYYYMMDD_HHMM.jsonl)

    Returns:
        Final validation loss value, or None if not found
    """
    # Extract timestamp from training JSONL: "train_YYYYMMDD_HHMM.jsonl"
    stem = jsonl_path.stem
    timestamp = stem[-13:]  # e.g., "20260621_1436"
    val_path = jsonl_path.parent / f"val_{timestamp}.jsonl"

    if not val_path.exists():
        return None

    try:
        with open(val_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    record = json.loads(line)
                    # Return the last (final) validation loss record
                    final_loss = record.get("validation_loss")
        return final_loss
    except (json.JSONDecodeError, IOError):
        return None


def compute_moving_average(values: List[float], window: int = 5) -> List[float]:
    """
    Compute moving average of values.

    Args:
        values: List of values to average
        window: Window size for moving average

    Returns:
        List of moving averages (same length as input, with padding at start)
    """
    if len(values) < window:
        return values

    moving_avg = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        avg = sum(values[start:i + 1]) / (i - start + 1)
        moving_avg.append(avg)
    return moving_avg


def plot_loss(records: List[Dict], jsonl_path: Path = None) -> bool:
    """
    Plot training loss and save alongside JSONL file.
    Includes raw training loss (light blue), moving average (dark blue),
    and final validation loss as a bright purple X marker.

    Args:
        records: List of loss records
        jsonl_path: Path to JSONL file (used to determine output location)

    Returns:
        True if plot was created successfully, False otherwise
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("⚠ matplotlib not installed. Install with: uv pip install matplotlib")
        return False

    if not records:
        print("No loss data to plot")
        return False

    steps = [r["step"] for r in records]
    losses = [r["loss"] for r in records]

    # Compute 5-step moving average
    moving_avg = compute_moving_average(losses, window=5)

    # Determine output path
    if jsonl_path:
        # Extract timestamp from JSONL filename and create matching plot name
        # JSONL file: "train_YYYYMMDD_HHMM.jsonl"
        # Plot file: "train_YYYYMMDD_HHMM.png"
        stem = jsonl_path.stem
        # Extract the timestamp part (last 13 characters: YYYYMMDD_HHMM)
        timestamp = stem[-13:]  # e.g., "20260621_1436"
        output_path = jsonl_path.parent / f"train_{timestamp}.png"
    else:
        output_path = Path("logs/training_loss_plot.png")

    try:
        plt.figure(figsize=(12, 6))

        # Plot raw training loss in light blue with transparency
        plt.plot(
            steps,
            losses,
            marker="o",
            linestyle="-",
            markersize=5,
            linewidth=2,
            color="#6ba3d6",
            alpha=0.6,
            label="Training Loss (raw)",
        )

        # Plot moving average in dark blue with transparency
        plt.plot(
            steps,
            moving_avg,
            linestyle="-",
            linewidth=2.5,
            color="#1f77b4",
            alpha=0.8,
            label="Moving Avg (5-step)",
        )

        # Add final validation loss as a bright purple X at the final step
        val_loss = load_validation_loss(jsonl_path) if jsonl_path else None
        if val_loss is not None:
            final_step = steps[-1]
            plt.plot(
                final_step,
                val_loss,
                marker="x",
                markersize=18,
                linewidth=3.5,
                color="#d62cf0",
                label=f"Final Validation Loss ({val_loss:.6f})",
                zorder=5,
            )

        plt.xlabel("Training Step", fontsize=11)
        plt.ylabel("Loss", fontsize=11)
        plt.title("Training Loss Over Time", fontsize=12, fontweight="bold")
        plt.legend(loc="best", fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150)
        print(f"✓ Plot saved to: {output_path}")
        if val_loss is not None:
            print(f"  Final validation loss: {val_loss:.6f}")
        plt.close()
        return True
    except Exception as e:
        print(f"✗ Error saving plot: {e}")
        plt.close()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Analyze training loss from JSONL files and create plots"
    )
    parser.add_argument("path", help="Path to JSONL file or directory with JSONL files")
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Skip plot generation (default: plots are created)",
    )

    args = parser.parse_args()
    path = Path(args.path)

    if not path.exists():
        print(f"Error: Path not found: {path}")
        sys.exit(1)

    # Find all JSONL files
    if path.is_file():
        jsonl_files = [path] if path.suffix == ".jsonl" else []
    else:
        jsonl_files = sorted(path.glob("*.jsonl"))

    if not jsonl_files:
        print(f"No .jsonl files found in {path}")
        sys.exit(1)

    print(f"Found {len(jsonl_files)} loss file(s)")

    # Analyze each file
    for jsonl_file in jsonl_files:
        records = load_loss_records(jsonl_file)
        if records:
            print_analysis(jsonl_file, records)

            # Create plot automatically unless --no-plot is specified
            if not args.no_plot:
                plot_loss(records, jsonl_file)
        else:
            print(f"✗ No records found in {jsonl_file.name}")


if __name__ == "__main__":
    main()

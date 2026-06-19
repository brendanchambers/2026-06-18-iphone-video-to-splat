#!/usr/bin/env python3
"""
Plot training loss from OpenSplat pipeline log file.
Reads logs/opensplat_pipeline.log and generates a loss curve plot.
"""

import re
import sys
from pathlib import Path
import matplotlib.pyplot as plt


def parse_training_loss(log_file):
    """
    Parse training loss from log file.

    Expected format: "Step {step}: {loss} ({percentage}%)"
    Returns: lists of (steps, losses)
    """
    steps = []
    losses = []

    try:
        with open(log_file, 'r') as f:
            for line in f:
                # Match pattern: "Step 10: 0.263509 (1%)"
                match = re.search(r'Step\s+(\d+):\s+([\d.]+)\s+\(\d+%\)', line)
                if match:
                    step = int(match.group(1))
                    loss = float(match.group(2))
                    steps.append(step)
                    losses.append(loss)
    except FileNotFoundError:
        print(f"Error: Log file not found: {log_file}")
        sys.exit(1)

    if not steps:
        print("Error: No training loss data found in log file")
        sys.exit(1)

    return steps, losses


def moving_average(values, window_size=10):
    """
    Calculate moving average with a given window size.
    """
    if len(values) < window_size:
        window_size = len(values)

    moving_avg = []
    for i in range(len(values)):
        start = max(0, i - window_size // 2)
        end = min(len(values), i + window_size // 2 + 1)
        moving_avg.append(sum(values[start:end]) / (end - start))

    return moving_avg


def plot_loss(steps, losses, output_path):
    """
    Create and save a loss plot with moving average.
    """
    # Calculate moving average
    ma_losses = moving_average(losses, window_size=10)

    plt.figure(figsize=(10, 6))
    plt.plot(steps, losses, linewidth=2, marker='o', markersize=4,
             label='Raw Loss', color='lightblue', alpha=0.8)
    plt.plot(steps, ma_losses, linewidth=2,
             label='Moving Average', color='darkblue', alpha=0.8)
    plt.xlabel('Training Step', fontsize=12)
    plt.ylabel('Loss', fontsize=12)
    plt.title('OpenSplat Training Loss', fontsize=14, fontweight='bold')
    plt.legend(loc='upper right', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # Save the plot
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {output_path}")

    # Print statistics
    min_loss = min(losses)
    max_loss = max(losses)
    avg_loss = sum(losses) / len(losses)

    print(f"\nLoss Statistics:")
    print(f"  Min loss: {min_loss:.6f}")
    print(f"  Max loss: {max_loss:.6f}")
    print(f"  Average loss: {avg_loss:.6f}")
    print(f"  Total steps: {len(steps)}")


def main():
    # Get project root (parent of scripts directory)
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    log_file = project_root / "logs" / "opensplat_pipeline.log"
    output_file = project_root / "logs" / "training_loss.png"

    print(f"Reading training loss from: {log_file}")
    steps, losses = parse_training_loss(log_file)

    print(f"Found {len(steps)} training steps")
    plot_loss(steps, losses, output_file)


if __name__ == "__main__":
    main()

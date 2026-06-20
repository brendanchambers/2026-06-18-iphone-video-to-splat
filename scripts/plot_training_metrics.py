#!/usr/bin/env python3
"""
Plot training and validation loss from OpenSplat pipeline log file.
Reads logs/opensplat_pipeline.log and generates a loss curve plot with both metrics.
"""

import re
import sys
from pathlib import Path
import matplotlib.pyplot as plt


def parse_training_loss(log_file):
    """
    Parse per-step training loss from log file.

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


def parse_validation_loss(log_file):
    """
    Parse final validation loss from log file.

    Expected format: "{image_path} validation loss: {loss_value}"
    Returns: float value of validation loss, or None if not found
    """
    try:
        with open(log_file, 'r') as f:
            for line in f:
                # Match pattern: ".../frame_0032.jpg validation loss: 0.0445"
                match = re.search(r'validation loss:\s+([\d.]+)', line)
                if match:
                    return float(match.group(1))
    except FileNotFoundError:
        pass

    return None


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


def plot_loss(steps, losses, val_loss, output_path):
    """
    Create and save a loss plot with training loss curve and validation loss reference line.
    """
    # Calculate moving average
    ma_losses = moving_average(losses, window_size=10)

    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot training loss
    ax.plot(steps, losses, linewidth=2, marker='o', markersize=4,
            label='Training Loss (Raw)', color='lightblue', alpha=0.8)
    ax.plot(steps, ma_losses, linewidth=2.5,
            label='Training Loss (Moving Avg)', color='darkblue', alpha=0.9)

    # Plot validation loss as horizontal line
    if val_loss is not None:
        ax.axhline(y=val_loss, color='red', linestyle='--', linewidth=2,
                   label=f'Validation Loss ({val_loss:.6f})', alpha=0.8)

    ax.set_xlabel('Training Step', fontsize=12)
    ax.set_ylabel('Loss', fontsize=12)
    ax.set_title('OpenSplat Training vs Validation Loss', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    # Save the plot
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {output_path}")

    # Print statistics
    min_loss = min(losses)
    max_loss = max(losses)
    avg_loss = sum(losses) / len(losses)
    final_loss = losses[-1]

    print(f"\nTraining Loss Statistics:")
    print(f"  Min loss:     {min_loss:.6f}")
    print(f"  Max loss:     {max_loss:.6f}")
    print(f"  Average loss: {avg_loss:.6f}")
    print(f"  Final loss:   {final_loss:.6f}")
    print(f"  Total steps:  {len(steps)}")

    if val_loss is not None:
        print(f"\nValidation Loss:")
        print(f"  Final validation loss: {val_loss:.6f}")
        ratio = val_loss / final_loss if final_loss > 0 else 0
        print(f"  Validation/Training ratio: {ratio:.4f}")
        if ratio > 1.1:
            print("  ⚠️  Model may be overfitting (val loss > 1.1x train loss)")
        elif ratio < 0.9:
            print("  ✓ Model generalizing well (val loss < 0.9x train loss)")
        else:
            print("  ✓ Validation and training loss are balanced")


def main():
    # Get project root (parent of scripts directory)
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    log_file = project_root / "logs" / "opensplat_pipeline.log"
    output_file = project_root / "logs" / "training_loss.png"

    print(f"Reading logs from: {log_file}\n")

    # Parse training loss
    steps, losses = parse_training_loss(log_file)
    print(f"Found {len(steps)} training steps")

    # Parse validation loss
    val_loss = parse_validation_loss(log_file)
    if val_loss is not None:
        print(f"Found validation loss: {val_loss:.6f}")
    else:
        print("No validation loss found in log")

    print()
    plot_loss(steps, losses, val_loss, output_file)


if __name__ == "__main__":
    main()

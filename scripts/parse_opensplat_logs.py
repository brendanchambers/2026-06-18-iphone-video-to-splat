#!/usr/bin/env python3
"""
Parse OpenSplat training and validation logs.
Extracts training loss (per-step) and final validation loss.
Saves results to structured JSON files for analysis and visualization.
"""

import re
import json
import sys
from pathlib import Path
from datetime import datetime


def parse_training_loss(log_file):
    """
    Parse per-step training loss from log file.

    Expected format: "Step {step}: {loss} ({percentage}%)"
    Returns: dict with keys 'steps' and 'losses'
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
        return None

    if not steps:
        print("Warning: No training loss data found in log file")
        return None

    return {
        'steps': steps,
        'losses': losses,
        'count': len(steps),
        'min': min(losses),
        'max': max(losses),
        'avg': sum(losses) / len(losses)
    }


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


def main():
    # Get project root (parent of scripts directory)
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    log_file = project_root / "logs" / "opensplat_pipeline.log"

    if not log_file.exists():
        print(f"Error: Log file not found: {log_file}")
        sys.exit(1)

    print(f"Parsing logs from: {log_file}\n")

    # Parse training loss
    print("=" * 60)
    print("TRAINING LOSS")
    print("=" * 60)
    training_data = parse_training_loss(log_file)

    if training_data:
        print(f"Found {training_data['count']} training steps")
        print(f"  Min loss:     {training_data['min']:.6f}")
        print(f"  Max loss:     {training_data['max']:.6f}")
        print(f"  Average loss: {training_data['avg']:.6f}")
        print(f"  Final loss:   {training_data['losses'][-1]:.6f}")
    else:
        print("No training loss data found")
        training_data = {}

    # Parse validation loss
    print("\n" + "=" * 60)
    print("VALIDATION LOSS")
    print("=" * 60)
    val_loss = parse_validation_loss(log_file)

    if val_loss is not None:
        print(f"Final validation loss: {val_loss:.6f}")
        # Calculate overfitting indicator
        if training_data and training_data['losses']:
            final_train_loss = training_data['losses'][-1]
            ratio = val_loss / final_train_loss if final_train_loss > 0 else 0
            print(f"Validation/Training ratio: {ratio:.4f}")
            if ratio > 1.1:
                print("⚠️  Model may be overfitting (val loss > 1.1x train loss)")
            elif ratio < 0.9:
                print("✓ Model generalizing well (val loss < 0.9x train loss)")
            else:
                print("✓ Validation and training loss are balanced")
    else:
        print("No validation loss found in log")
        val_loss = None

    # Save results to JSON
    print("\n" + "=" * 60)
    print("SAVING RESULTS")
    print("=" * 60)

    results = {
        'timestamp': datetime.now().isoformat(),
        'log_file': str(log_file),
        'training': training_data,
        'validation': {
            'final_loss': val_loss,
            'found': val_loss is not None
        }
    }

    results_file = project_root / "logs" / "opensplat_loss_summary.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to: {results_file}")
    print("\nDone!")


if __name__ == "__main__":
    main()

# Training Loss Logging

## Overview

The pipeline automatically records training loss from OpenSplat to JSONL format, enabling post-training analysis and visualization. Each training step's loss is captured in real-time during training and stored alongside the 3D Gaussian Splat PLY file.

## Output Files

During training, two output files are created in `data/intermediates/{experiment}/splats/`:

```
current_scene_20260621_1430.ply     ← 3D Gaussian Splat model
current_scene_20260621_1430.jsonl   ← Training loss log
```

The `.jsonl` file contains one JSON object per training step, enabling efficient streaming and analysis.

## JSONL Format

Each line is a complete JSON object:

```json
{"step": 10, "loss": 0.335803, "timestamp": "2026-06-21T14:30:00.123456"}
{"step": 20, "loss": 0.316211, "timestamp": "2026-06-21T14:30:10.234567"}
{"step": 30, "loss": 0.283803, "timestamp": "2026-06-21T14:30:20.345678"}
```

**Fields:**
- `step`: Training iteration number (from OpenSplat training steps)
- `loss`: Loss value (float)
- `timestamp`: ISO 8601 formatted timestamp when loss was recorded

**Note:** Steps are logged at intervals determined by OpenSplat's output frequency (typically every 10 iterations). Not every step is recorded, only those printed to stdout.

## Usage

### Automatic During Training

Loss files are created automatically when you run the pipeline:

```bash
uv run python pipeline.py
```

### Post-Training Analysis

#### Show Statistics

```bash
uv run python scripts/analyze_training_loss.py data/intermediates/current_scene/splats/current_scene_20260621_1430.jsonl
```

Output:
```
Training Loss Analysis: current_scene_20260621_1430.jsonl
==================================================
Total steps:     1500
Step range:      0 → 1499
Min loss:        0.031456
Max loss:        1.425634
Average loss:    0.145123
Final loss:      0.032145
==================================================
```

#### Generate Plot

```bash
uv run python scripts/analyze_training_loss.py --plot data/intermediates/current_scene/splats/current_scene_20260621_1430.jsonl
```

Saves plot to `logs/training_loss_plot.png`

#### Batch Analysis

Analyze all loss files in a directory:

```bash
uv run python scripts/analyze_training_loss.py data/intermediates/current_scene/splats/
```

## Parsing Loss Files Programmatically

### Python

```python
import json

# Read loss records
records = []
with open("current_scene_20260621_1430.jsonl") as f:
    for line in f:
        records.append(json.loads(line))

# Extract data
steps = [r["step"] for r in records]
losses = [r["loss"] for r in records]

# Calculate statistics
min_loss = min(losses)
final_loss = losses[-1]
```

### Shell

```bash
# Extract all loss values
cat current_scene_20260621_1430.jsonl | jq '.loss'

# Find minimum loss
cat current_scene_20260621_1430.jsonl | jq '.loss' | sort -n | head -1

# Get final loss value
cat current_scene_20260621_1430.jsonl | tail -1 | jq '.loss'
```

## Integration with Other Tools

The JSONL format is compatible with many data science tools:

- **pandas**: `pd.read_json(..., lines=True)`
- **duckdb**: `SELECT * FROM read_json_auto('file.jsonl')`
- **jq**: Command-line JSON processing
- **Streamlit**: Real-time training monitoring dashboards

Example with pandas:

```python
import pandas as pd

df = pd.read_json("current_scene_20260621_1430.jsonl", lines=True)
print(df.describe())
```

## Implementation Details

### Loss Parsing

The parser (`src.opensplat_trainer.parse_opensplat_loss`) uses regex to extract loss from OpenSplat output:

```python
# Matches OpenSplat format: "Step 10: 0.335803 (20%)"
match = re.search(r"Step\s+(\d+):\s+([\d.]+)\s*\(\d+%\)", line)
```

This pattern matches:
- Step number: `\d+` (one or more digits)
- Loss value: `[\d.]+` (digits and decimal point)
- Progress percentage: `\(\d+%\)` (e.g., "(20%)", "(100%)")

### File Naming

Output files use the same timestamp suffix for easy correlation:

```
{experiment}_{YYYYMMDD}_{HHMM}.ply
{experiment}_{YYYYMMDD}_{HHMM}.jsonl
```

This allows quick matching between model outputs and training logs.

## Troubleshooting

### No JSONL file created

Ensure training runs to completion. The loss file is created during training, so if OpenSplat exits early, fewer (or no) loss records will be written.

### Loss values seem wrong

Check the OpenSplat log to verify the loss format. The parser expects `Step N: loss=X.XXX`. If OpenSplat's output format has changed, the regex pattern may need updating in `src/opensplat_trainer.py:30`.

### Missing specific steps

Not every step may be logged by OpenSplat. The parser only records steps that appear in stdout. This is expected behavior.

## See Also

- `CLAUDE.md` - Development notes on implementation
- `src/opensplat_trainer.py` - Loss parsing implementation
- `scripts/analyze_training_loss.py` - Analysis utility source code
- `test_loss_parsing.py` - Test suite for loss parsing

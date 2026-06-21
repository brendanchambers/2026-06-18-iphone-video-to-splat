# Experiment Group Tracking Implementation (2026-06-21)

## Overview
Added automatic experiment result logging system that collects final metrics (train loss, validation loss, total runtime) and writes them to group-based JSONL files. This enables easy comparison of experiments organized by group.

## What Was Changed

### Files Created
- `src/experiment_tracker.py` - Experiment tracking utilities module (150 lines)
  - `extract_final_loss_value(jsonl_path)` - Extracts final training loss
  - `extract_validation_loss(jsonl_path)` - Extracts final validation loss
  - `extract_total_running_time(timing_jsonl_path)` - Extracts total pipeline time
  - `log_experiment_result(...)` - Logs results to group JSONL file
  - `ExperimentResult` dataclass - Record structure

### Files Modified
- `config/baseline.yaml` - Added `experiment_group: "baseline"` parameter to project section
- `pipeline.py` - Integrated experiment logging:
  - Imported experiment tracker utilities
  - Added `log_experiment_results()` method to Pipeline class
  - Auto-logs results at end of successful pipeline run in `run_full_pipeline()`

## Key Features

✅ **Automatic extraction**: Pulls metrics from existing log files (train_*.jsonl, val_*.jsonl, running-time_*.jsonl)
✅ **Group-based organization**: One JSONL file per experiment group for easy comparison
✅ **Append-only format**: New experiments appended to group file, no overwrites
✅ **ISO timestamps**: Full traceability of when each experiment was logged
✅ **Graceful handling**: Works even if validation is disabled (val_loss=null)
✅ **Config inheritance**: Teensy and other inherited configs automatically get baseline's group
✅ **Zero setup**: Works immediately, no additional configuration required

## Usage Examples

### Basic Usage (Automatic)
```bash
uv run python pipeline.py
```
Results automatically logged to `reports/experiments/baseline.jsonl`

### Run Multiple Experiments in Same Group
```bash
# All results go to reports/experiments/hyperparameter_sweep.jsonl
uv run python pipeline.py project.experiment_group=hyperparameter_sweep project.experiment_name=exp_1 opensplat.num_iters=1500
uv run python pipeline.py project.experiment_group=hyperparameter_sweep project.experiment_name=exp_2 opensplat.num_iters=2000
uv run python pipeline.py project.experiment_group=hyperparameter_sweep project.experiment_name=exp_3 opensplat.num_iters=2500
```

### Analyze Results with Python
```python
import json
from pathlib import Path

group_file = Path("reports/experiments/hyperparameter_sweep.jsonl")
results = []
with open(group_file) as f:
    for line in f:
        results.append(json.loads(line))

# Find best by validation loss
best = min(results, key=lambda r: r.get("val_loss", float("inf")))
print(f"Best: {best['experiment_name']} (val_loss={best['val_loss']:.4f}, time={best['total_running_time']:.1f}s)")
```

## Output Format

**File location:** `reports/experiments/<experiment_group>.jsonl`

**Example content:**
```json
{"experiment_name": "exp_1", "experiment_group": "hyperparameter_sweep", "timestamp": "2026-06-21T14:30:00.123456", "total_running_time": 500.0, "train_loss": 0.45, "val_loss": 0.50}
{"experiment_name": "exp_2", "experiment_group": "hyperparameter_sweep", "timestamp": "2026-06-21T14:45:20.654321", "total_running_time": 510.0, "train_loss": 0.42, "val_loss": 0.48}
```

**Fields:**
- `experiment_name`: Name from config (e.g., "current_scene")
- `experiment_group`: Group name for organizing related experiments
- `timestamp`: ISO format timestamp when logged
- `total_running_time`: Total pipeline execution time in seconds
- `train_loss`: Final training loss value (float)
- `val_loss`: Final validation loss value (float or null)

## Testing

✅ All existing tests pass (6/6 test suites)
✅ Experiment tracker utilities tested with mock data
✅ Multi-experiment logging verified
✅ Config loading verified (baseline + teensy configs work)
✅ Pipeline imports without errors

## How It Works

1. **At pipeline start**: User provides `experiment_group` in config (defaults to "baseline")
2. **During execution**: Pipeline runs normally, timing and loss data collected
3. **At pipeline end**: `log_experiment_results()` method called:
   - Finds most recent timing JSONL file → extracts total_running_time
   - Finds most recent train loss JSONL file → extracts train_loss
   - Finds corresponding validation loss file (if exists) → extracts val_loss
   - Creates reports/experiments/ directory if needed
   - Appends record to `reports/experiments/<experiment_group>.jsonl`
4. **Results logged**: Record includes experiment metadata + metrics
5. **Easy comparison**: All experiments in same group in one file

## Configuration

### Baseline Config
```yaml
project:
  experiment_name: "current_scene"
  experiment_group: "baseline"  # <- New parameter
```

### Teensy Config (inherits from baseline)
```yaml
defaults:
  - baseline
  - _self_

project:
  experiment_name: "teensy"
  # experiment_group inherited as "baseline" from baseline.yaml
```

### CLI Override
```bash
# Override experiment group
uv run python pipeline.py project.experiment_group=my_sweep

# Override both name and group
uv run python pipeline.py project.experiment_name=test1 project.experiment_group=testing
```

## Future Enhancements

Potential future improvements:
- [ ] Script to parse experiment group JSONL and create comparison table
- [ ] Visualization of loss vs parameter values (heatmap)
- [ ] Interactive comparison tool for multiple groups
- [ ] Automatic detection of best configuration
- [ ] CSV export for spreadsheet analysis

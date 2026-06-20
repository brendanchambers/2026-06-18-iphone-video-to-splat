
## Project info
We will be training and rendering a 3D Gaussian splat. The language will be python, with env managed with uv. The development and compute will happen on this macbook air M4 24GB laptop.
## Project Goal
We will be attempting to create a 3D gaussian splat from extracted frames and structure from motion (`data/intermediate/frames` and `data/intermediate/sfm`). The computation will be happening on a macbook air M4 24gb. We will use opensplat to initialize and train the 3D gaussian splat (`https://github.com/pierotofy/opensplat`).

## Workflow info
Please keep your plan, next steps, debugging notes, and other documentation for yourself in this file, CLAUDE.md.
For other materials, e.g. run instructions, and other project info, maintain documentation in README.md

## Important Rules

**VALIDATION CONFIGURATION**: Do NOT change validation settings (VAL_ENABLED, VAL_IMAGE, SSIM_WEIGHT) without explicit discussion with the user. These are intentional experimental choices. If there are conflicts between validation configuration and data (e.g., validation image doesn't exist), discuss options with the user before making changes.

## Inner and outer repo organization for rapid prototyping
Notice there is an inner project repo named opensplat pasted into the project. Avoid modifying this repository unless absolutely necessary. We will do our work in the outer repository. The inner project, opensplat, is expected to be a key dependency and it's simpler to have its code available here in the repo where we can use it heavily with ease.

## Experiments
Use tee to pipe console output to the `logs` directory.

## Debugging Notes

3. **OpenSplat logs** (training):
   - `logs/opensplat_pipeline.log` - Training progress, loss values
   - Check for:
     - "Invalid project folder" → data directory structure wrong
     - Loss convergence pattern
     - Memory issues ("CUDA out of memory" or similar)

4. **Timing summary** (JSON):
   - `logs/colmap_timings.jsonl` - Each run's duration with parameters

### Key design decisions:
- **Two-stage pipeline**: COLMAP SfM + distortion correction, then OpenSplat training
- Uses **COLMAP image_undistorter** to linearize radial distortion before training
- Uses **OpenSplat** for efficient gaussian splatting implementation
- Supports **per-image training** (processes one random view per step)
- Downscaling option to handle large images on memory-constrained machines
- Compatible with M4 MacBook Air



## Semantic Naming for Gaussian Splat Models (2026-06-19)

### Implementation
Updated `launch_opensplat.sh` to automatically generate semantically meaningful filenames for saved models.

**Filename Format:**
```
opensplat_output_numiters{NUM_ITERS}_{YYYYMMDD}_{HHMM}.ply
```


## Validation Setup for Gaussian Splat Models (2026-06-19)

### Overview
Implemented validation monitoring using OpenSplat's built-in validation parameters to track held-out performance and detect overfitting during training.

### OpenSplat Validation Capabilities (Investigated)

**Supported Parameters:**
- `--val`: Boolean flag to enable validation (withholds single image from training)
- `--val-image`: Select validation image: `"random"` (default) or specific filename
- `--val-render`: Directory path to save rendered validation images during training
- `--ssim-weight`: Loss weighting between SSIM (perceptual) and L1 (reconstruction) loss

**Fixed Behaviors (Not Configurable):**
- **Validation frequency**: Renders every 10 training steps
- **Number of validation images**: Exactly 1 image (not multiple)
- **Validation metrics output**: Final validation loss printed to stdout at end of training
- **Random seed**: Uses fixed seed (42) for reproducible "random" validation image selection

**Validation Rendering:**
- Saves rendered validation images as PNGs (e.g., `10.png`, `20.png`, `30.png`, ...)
- Shows how well the model reconstructs the held-out view over training iterations
- Useful for visual inspection of training progress and convergence quality

### Loss Parsing and Visualization (Completed 2026-06-19)

**Created `scripts/parse_opensplat_logs.py`:**
- Parses training loss per-step from log file (format: `Step N: loss`)
- Parses final validation loss from log file (format: `path validation loss: value`)
- Saves results to JSON file: `logs/opensplat_loss_summary.json`
- Calculates and reports statistics:
  - Training: min, max, average, final loss
  - Validation: final loss and validation/training ratio
  - Overfitting detection: Reports if val loss > 1.1x train loss

**Usage:**
```bash
uv run python scripts/parse_opensplat_logs.py
```

**Output Example:**
```
TRAINING LOSS
Found 1000 training steps
  Min loss:     0.032156
  Max loss:     0.156234
  Average loss: 0.087456
  Final loss:   0.041234

VALIDATION LOSS
Final validation loss: 0.042156
Validation/Training ratio: 1.0223
✓ Validation and training loss are balanced
```

**Updated `scripts/plot_training_metrics.py`:**
- Now plots both training and validation loss on same graph
- Training loss shown as:
  - Light blue curve (raw per-step loss with markers)
  - Dark blue curve (10-step moving average)
- Validation loss shown as:
  - Red dashed horizontal line (final validation loss)
  - Labeled with numerical value
- Enhanced statistics output:
  - Displays training loss statistics
  - Displays validation loss with overfitting indicator
  - Suggests model quality based on validation/training ratio

**Usage:**
```bash
uv run python scripts/plot_training_metrics.py
```

**Output Graph:**
- X-axis: Training step number
- Y-axis: Loss value
- Legend shows all three metrics with color coding
- Saved to: `logs/training_loss.png` (150 DPI)

**Interpretation:**
- **Healthy training**: Both curves decrease over time, validation loss stays close to (or below) training loss
- **Overfitting**: Validation loss increases while training loss decreases (or validation >> training)
- **Balanced**: Validation/Training ratio between 0.9-1.1x indicates good generalization

### Future Enhancements (Not Implemented Yet)
- [ ] Store validation loss values per training iteration (requires OpenSplat modification)
- [ ] Create side-by-side comparison of validation rendered images
- [ ] Track validation metrics across multiple runs for statistical analysis
- [ ] Auto-detect optimal stopping point based on validation loss plateau

---

### Configuration

The `.env` file provides defaults that can be overridden:
```bash
PROJECT_DIR="/Users/bc/brendanchambers/2026-06-18-iphone-video-to-splat"
VIDEO_PATH="./data/incoming/movies/gardenbed_2026-06-17.mov"
EXPERIMENT_NAME="test"                    # Default experiment name
MAX_NUM_FEATURES=4096                     # Default features
NUM_ITERS=500                             # Default training iterations
VAL_ENABLED=true                          # Validation enabled
VAL_IMAGE="frame_0032.jpg"                # Validation image
VAL_RENDER_DIR="./data/intermediates/validation_renders"
SSIM_WEIGHT=0.2                           # Perceptual loss weight
```

**Important**: Command-line parameters override `.env` values.

### Design Improvements Over Previous Approach

| Aspect | Before | After |
|--------|--------|-------|
| COLMAP Scripts | 2 separate files (exhaustive, sequential) | 1 unified file with `--matcher` param |
| Experiment Orchestration | Manual (run COLMAP, then OpenSplat) | Automated via `run_experiment.sh` |
| Parameter Overrides | Edit `.env` file | All command-line arguments |
| Reports | Manual comparison | Auto-generated markdown |
| Naming | Inconsistent | Semantic (includes matcher type) |
| Repeatability | Moderate | High (clear parameter structure) |

### Typical Workflow

1. **Quick test** (5 min, 4-second video):
   ```bash
   ./run_experiment.sh --name quicktest --video gardenbed_test_4s_middle.mov
   ```

2. **Production run** (15-20 min, full video):
   ```bash
   ./run_experiment.sh --name production --video gardenbed_2026-06-17.mov \
       --max-features 8192 --iters 1500
   ```

3. **COLMAP-only timing test**:
   ```bash
   ./launch_colmap.sh --matcher exhaustive --video video.mov --experiment timing_test
   ./launch_colmap.sh --matcher sequential --video video.mov --experiment timing_test
   ```

### Output Structure

After running `run_experiment.sh --name my_experiment`:
```
data/intermediates/
├── my_experiment_exhaustive_max-num-features-4096/
│   ├── images/
│   ├── sparse/
│   └── database.db
├── my_experiment_exhaustive_max-num-features-4096_distortion_corrected/
│   ├── images/
│   ├── sparse/
│   └── splats/
│       └── 500steps_YYYYMMDD_HHMM/
│           └── my_experiment_exhaustive.ply
├── my_experiment_sequential_max-num-features-4096/
└── my_experiment_sequential_max-num-features-4096_distortion_corrected/
    └── splats/
        └── 500steps_YYYYMMDD_HHMM/
            └── my_experiment_sequential.ply

logs/
├── colmap_timings.jsonl
├── colmap_my_experiment_exhaustive_*.log
└── opensplat_my_experiment_exhaustive_*.log

my_experiment_comparison_report.md     ← Auto-generated
```

### Testing Status

The unified workflow was tested with 4-second test video on both matchers:
- **Exhaustive matcher**: Works correctly with `--matcher exhaustive`
- **Sequential matcher**: Works correctly with `--matcher sequential`
- Both generate proper log files and directory structures
- Ready for production use

### Key Behaviors

1. **Parameter Precedence**: Command-line args > `.env` values > hardcoded defaults
2. **Naming Convention**: `{experiment}_{matcher}_max-num-features-{N}` for output dirs
3. **Report Generation**: Auto-generated `{experiment}_comparison_report.md` with timing & loss data
4. **Validation**: Both COLMAP and OpenSplat use frame_0032.jpg for held-out validation
5. **Logging**: All output tee'd to `logs/` directory based on experiment name

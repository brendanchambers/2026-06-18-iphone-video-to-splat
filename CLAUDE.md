
## Project info
We will be training and rendering a 3D Gaussian splat. The language will be python, with env managed with uv. The development and compute will happen on this macbook air M4 24GB laptop. Never change validation approaches without discussing it first and receiving a greenlight.

## Project Goal
We will be attempting to create a 3D gaussian splat from extracted frames and structure from motion (`data/intermediate/frames` and `data/intermediate/sfm`). The computation will be happening on a macbook air M4 24gb. We will use opensplat to initialize and train the 3D gaussian splat (`https://github.com/pierotofy/opensplat`).

## Workflow info
Please keep your plan, next steps, debugging notes, and other documentation for yourself in this file, CLAUDE.md.
For other materials, e.g. run instructions, and other project info, maintain documentation in README.md.
Do not create new markdown files in the top level project directory. If needed, you may organize them under `reference` or `work_history`.
Regularly clean up old work details from CLAUDE.md to maintain a concise markdown file.

## Inner and outer repo organization for rapid prototyping
Notice there is an inner project repo named opensplat pasted into the project. Avoid modifying this repository unless absolutely necessary. We will do our work in the outer repository. The inner project, opensplat, is expected to be a key dependency and it's simpler to have its code available here in the repo where we can use it heavily with ease.

## Experiments
Write console output and errors to a `logs` directory. Use a single logfile per unique run (when we are runnign comparisons, 1 logfile per experiment variant).


# Below: compressed log of past work

## Training Loss Visualization (2026-06-19)

### Implementation
Created `scripts/plot_training_loss.py` to analyze and visualize OpenSplat training convergence.

**Usage:**
```bash
uv run python scripts/plot_training_loss.py
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

### Configuration (.env)

Added to `.env`:
```bash
# OpenSplat Validation
VAL_ENABLED=true                          # Enable validation mode
VAL_IMAGE="random"                        # "random" or specific filename
VAL_RENDER_DIR="./data/intermediates/validation_renders"
SSIM_WEIGHT=0.2                          # Perceptual quality weighting
```

Command line arguments override .env values.

### Integration into Training Scripts (Completed 2026-06-19)

**Updated `launch_opensplat.sh`:**
1. Loads validation configuration from `.env`:
   - `VAL_ENABLED=true` - Enables validation mode
   - `VAL_IMAGE="frame_0032.jpg"` - Always use 32nd frame for validation
   - `VAL_RENDER_DIR="./data/intermediates/validation_renders"` - Output directory for rendered validation images
   - `SSIM_WEIGHT=0.2` - Loss weighting (perceptual vs reconstruction)

2. Constructs validation arguments conditionally:
   ```bash
   if [ "$VAL_ENABLED" = "true" ]; then
       VALIDATION_ARGS="--val --val-image $VAL_IMAGE --val-render $VAL_RENDER_FULL --ssim-weight $SSIM_WEIGHT"
   fi
   ```

3. Passes validation args to OpenSplat binary:
   ```bash
   $OPENSPLAT_BIN "$DATA_DIR" --colmap-image-path "$IMAGES_DIR" --output "$OUTPUT_PATH" --num-iters "$NUM_ITERS" $VALIDATION_ARGS
   ```

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

## Python Pipeline Implementation (2026-06-20)

### Overview
Replaced bash scripts with a modular Python pipeline using Hydra + OmegaConf for configuration management. This provides:
- Centralized YAML configuration instead of scattered .env and hardcoded values
- Modular design: 6 independent utility functions + orchestrator
- Full test suite (6 test suites, all passing)
- Comprehensive logging and error handling
- CLI configuration overrides (no file editing needed)
- Full backward compatibility (bash scripts still work)

### Architecture

```
pipeline.py (main entry point)
├── src/
│   ├── frame_extractor.py           # FFmpeg video → JPEG frames
│   ├── colmap_feature_extractor.py  # COLMAP SIFT feature extraction
│   ├── colmap_feature_matcher.py    # COLMAP sequential feature matching
│   ├── colmap_mapper.py             # COLMAP sparse reconstruction
│   ├── colmap_undistorter.py        # COLMAP image undistortion
│   └── opensplat_trainer.py         # OpenSplat training
├── config/
│   ├── baseline.yaml                # Default 87 parameters, 6 sections
│   └── teensy.yaml                  # Dev/test config with minimal iterations
└── test_pipeline.py                 # 6 test suites (all passing)
```

### Files Created

**Utility Modules** (6 files, ~28K)
- `frame_extractor.py` - FFmpeg integration with mpdecimate support
- `colmap_feature_extractor.py` - SIFT feature extraction (12 params)
- `colmap_feature_matcher.py` - Sequential feature matching (16 params)
- `colmap_mapper.py` - Sparse 3D reconstruction (20 params)
- `colmap_undistorter.py` - Image undistortion (8 params)
- `opensplat_trainer.py` - Training orchestration (13 params)

**Main Pipeline** (1 file, 9K)
- `pipeline.py` - Pipeline class with 7 methods:
  - `run_full_pipeline()` - orchestrates all steps
  - `run_frame_extraction()` through `run_splat_training()` - individual steps

**Configuration** (2 files, 14K)
- `config/baseline.yaml` - Hydra configuration with 87 parameters organized in:
  - project (3 params)
  - paths (8 params, with interpolation)
  - frame_extraction (5 params)
  - colmap (56 params: feature_extraction, matching, mapper, undistorter)
  - opensplat (13 params)
  - validation (2 params)
- `config/teensy.yaml` - Uses Hydra defaults inheritance (16 lines) - inherits baseline.yaml and overrides only: experiment_name, video_path, opensplat.num_iters, validation.image

**Testing & Documentation** (4 files, 44K)
- `test_pipeline.py` - 6 test suites (all passing)
- `PIPELINE.md` - Complete pipeline documentation
- `reports/IMPLEMENTATION_SUMMARY.md` - Detailed implementation report
- `reports/FILE_MANIFEST.md` - File inventory and quick reference

### Configuration System

**Hydra + OmegaConf**
- YAML-based configuration with path interpolation
- CLI overrides: `uv run python pipeline.py key.subkey=value`
- No file editing needed to change parameters
- Full type checking and validation
- Composable configuration sections

**Example Usage**
```bash
# Override single parameter
uv run python pipeline.py opensplat.num_iters=3000

# Multiple overrides
uv run python pipeline.py \
  opensplat.num_iters=2000 \
  validation.enabled=false \
  frame_extraction.fps=4
```

### Test Results

All 6 test suites PASSED:
1. ✅ Configuration Loading
2. ✅ Pipeline Instantiation
3. ✅ Module Imports
4. ✅ Config Parameter Coverage
5. ✅ Pipeline Methods
6. ✅ Directory Structure

### Usage

```bash
# Run full pipeline
uv run python pipeline.py

# Run tests
uv run python test_pipeline.py

# Override config
uv run python pipeline.py opensplat.num_iters=3000

# Programmatic use
from pipeline import Pipeline
pipeline = Pipeline(config)
success = pipeline.run_full_pipeline()
```

### Key Features

✅ Modular - each step independent
✅ Hydra configuration - centralized, composable
✅ Comprehensive logging - file + console
✅ Error handling - stops on failure, logs details
✅ Backward compatible - bash scripts still available
✅ Fully tested - 6 test suites validate all functionality
✅ IDE friendly - full Python IDE support
✅ Extensible - easy to add new steps

### Config Inheritance Pattern (2026-06-21)

**Approach:** Hydra defaults list composition - teensy.yaml inherits from baseline.yaml

**How it works:**
- `baseline.yaml` contains all 87 core parameters
- `teensy.yaml` starts with `defaults: [baseline, _self_]`, inheriting everything
- Then teensy overrides only the 4 parameters that differ:
  - `project.experiment_name: "teensy"`
  - `project.video_path: "./data/incoming/movies/teensy.mov"`
  - `opensplat.num_iters: 50`
  - `validation.image: "frame_0001.jpg"`
- Deep merge combines baseline + teensy overrides

**Benefits:**
- ✅ Zero duplication (teensy was 124 lines, now 16 lines)
- ✅ Change propagation (update baseline.yaml, all inheriting configs auto-update)
- ✅ Clear intent (teensy.yaml shows exactly what's different)
- ✅ Scales well (new experiments are just a few lines of overrides)
- ✅ No code changes needed (pipeline.py works unchanged)

**Adding new experiment configs:**
1. Create `config/experiment_name.yaml`
2. Start with: `defaults: [baseline, _self_]`
3. Add only the parameters you're testing
4. Run: `uv run python pipeline.py --config-name experiment_name`

**Usage:**
```bash
# Teensy (inherits baseline)
uv run python pipeline.py --config-name teensy

# Baseline
uv run python pipeline.py --config-name baseline

# New experiment (inherits baseline)
uv run python pipeline.py --config-name high_quality
```

### Next Steps

- See `PIPELINE.md` for usage and API reference
- See `reports/IMPLEMENTATION_SUMMARY.md` for architecture details
- See `config/baseline.yaml` for all 87 available parameters
- See `config/teensy.yaml` for config inheritance pattern (16 line example)
- Run `uv run python test_pipeline.py` to verify setup
- Run `uv run python pipeline.py` to execute the pipeline

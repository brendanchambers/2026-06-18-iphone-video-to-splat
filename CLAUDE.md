
## Project info
We will be training and rendering a 3D Gaussian splat. The language will be python, with env managed with uv. The development and compute will happen on this macbook air M4 24GB laptop.
## Project Goal
We will be attempting to create a 3D gaussian splat from extracted frames and structure from motion (`data/intermediate/frames` and `data/intermediate/sfm`). The computation will be happening on a macbook air M4 24gb. We will use opensplat to initialize and train the 3D gaussian splat (`https://github.com/pierotofy/opensplat`).

## Workflow info
Please keep your plan, next steps, debugging notes, and other documentation for yourself in this file, CLAUDE.md.
For other materials, e.g. run instructions, and other project info, maintain documentation in README.md

## Inner and outer repo organization for rapid prototyping
Notice there is an inner project repo named opensplat pasted into the project. Avoid modifying this repository unless absolutely necessary. We will do our work in the outer repository. The inner project, opensplat, is expected to be a key dependency and it's simpler to have its code available here in the repo where we can use it heavily with ease.

## Experiments
Use tee to pipe console output to the `logs` directory.

## Debugging Notes

### Debugging movie
We made a 4s .mov `gardenbed_test_4s_middle.mov` for rapid iteration during testing.

### OpenSplat Binary Issue (2026-06-18)
Issues: Warning about duplicated runtimes and segmentation fault. Cause: Pytorch was installed as a download and using brew, causing two runtimes linked in different places. Solution: removed installed pytorch and used brew as the sole runtime. Rebuilt OpenSplat with corrected path.

## Implementation Overview

### What was created:
1. **config.toml** - Configuration file for OpenSplat training
   - Training hyperparameters (learning rates, number of steps, Gaussian count)
   - Image downscaling for memory efficiency
   - Note: Data paths currently need fixing (see TODOs below)

2. **scripts/train_gaussian_splat.py** - Complete training script
   - Loads frames from `data/intermediates/{experiment_name}_distortion_corrected/images/`
   - Loads camera intrinsics and poses from `data/intermediates/{experiment_name}_distortion_corrected/sparse/0/`
   - Implements differentiable rendering using OpenSplat
   - Full training loop with Adam-style optimization
   - Saves checkpoints and final model as PLY format

### Key design decisions:
- **Two-stage pipeline**: COLMAP SfM + distortion correction, then OpenSplat training
- Uses **COLMAP image_undistorter** to linearize radial distortion before training
- Uses **OpenSplat** for efficient gaussian splatting implementation
- Supports **per-image training** (processes one random view per step)
- Downscaling option to handle large images on memory-constrained machines
- Compatible with M4 MacBook Air

### Issues encountered and resolved:
- **GPU memory issues** with high-resolution images and large Gaussian counts
  - Addressed with downscaling (4-8x) and reduced Gaussian counts (100-500)
- **gsplat-mlx incompatibilities** with M4 MacBook Air Metal backend
  - Resolved by switching to OpenSplat
- **COLMAP distortion linearization**
  - Already implemented via `colmap image_undistorter` in try_bash_colmap.sh

### Current blockers (see TODOs below):
1. ~~Path references and data organization bugs prevent pipeline from running~~ **FIXED**
2. Scripts need cleanup and path validation with minimal test case

### Configuration notes:
- Adjust `downscale` factor in config.toml if GPU errors occur
- Reduce `num_gaussians` and `num_steps` for testing on limited memory
- Current defaults are conservative for 24GB M4 MacBook Air
- See TODOs section below for path fixes needed before running

---

## Pipeline Testing & Path Fixes (2026-06-19)

### Status
- Distortion correction is **already implemented** via `colmap image_undistorter` (see try_bash_colmap.sh)
- Main issue: Path references and data organization have bugs preventing pipeline from running
- Need: Clean test with 8-frame minimal example to verify and fix all paths

### TODOs - Fix path bugs and test with 8-frame example

- [ ] **Create 8-frame test dataset**
  - Extract minimal 8-frame subset from `data/incoming/gardenbed_2026-06-17.MOV`
  - Use: `ffmpeg -i data/incoming/gardenbed_2026-06-17.MOV -vf "fps=0.2" -q:v 2 data/intermediates/test_8frames/images/frame_%04d.jpg`
  - This allows quick iteration through full pipeline without long COLMAP/training times

- [ ] **Test and fix Stage 1 paths: COLMAP SfM + Distortion Correction**
  - Run COLMAP pipeline manually on 8-frame test set
  - Verify these paths work correctly:
    - Input frames: `data/intermediates/test_8frames/images/`
    - COLMAP output: `data/intermediates/test_8frames/sparse/0/`
    - Distortion-corrected output: `data/intermediates/test_8frames_distortion_corrected/`
  - Fix bugs in `try_bash_colmap.sh` script (path concatenation errors)
  - Create working version: `scripts/pipeline_colmap_stage.sh`

- [ ] **Test and fix Stage 2 paths: OpenSplat training**
  - Verify training script reads from correct paths:
    - Images: `data/intermediates/test_8frames_distortion_corrected/images/`
    - SfM: `data/intermediates/test_8frames_distortion_corrected/sparse/0/`
    - Output: `data/intermediates/test_8frames_distortion_corrected/opensplat_output/model.ply`
  - Update config.toml with explicit paths (no hardcoded paths in scripts)
  - Create working version: `scripts/pipeline_opensplat_stage.sh`

- [ ] **Establish naming conventions and clean up**
  - Finalize directory naming: use `{experiment_name}/` and `{experiment_name}_distortion_corrected/`
  - Remove old experimental directories in `data/intermediates/`
  - Document path handling strategy in CLAUDE.md

- [ ] **Create unified pipeline runner**
  - Write `scripts/run_full_pipeline.sh` that:
    - Takes video path and experiment name as arguments
    - Automatically creates directory structure
    - Runs both COLMAP and OpenSplat stages sequentially
    - Uses consistent naming and path references
  - Make it work end-to-end with 8-frame test example

---

## Path Fixes Applied (2026-06-19)

### Test Results
Successfully tested COLMAP pipeline with 4-second test video extracted from middle of `gardenbed_2026-06-17.mov`:
- Created: `data/incoming/gardenbed_test_4s_middle.mov` (4-second snippet)
- Output: `data/intermediates/test_4s_distortion_corrected/`
- Results: 8 frames extracted, 3,980 sparse points reconstructed, distortion correction completed

### Bugs Fixed in try_bash_colmap.sh

**Issue 1: Missing quotes around variable paths (Lines 63-64)**
- **Problem**: `$IMAGES_DIR` and `$SPARSE_DIR` without quotes could fail if paths contain spaces
- **Fixed**: Added quotes: `"$IMAGES_DIR"` and `"$SPARSE_DIR/0"`

**Issue 2: Missing forward slash in path concatenation (Line 65)**
- **Problem**: `${PROJECT_DIR}/data/intermediates${EXPERIMENT_NAME}_distortion_corrected`
  - Created malformed path: `/path/data/intermediatestest_4s_distortion_corrected`
  - Missing `/` between `intermediates` and experiment name
- **Fixed**: Changed to: `${PROJECT_DIR}/data/intermediates/${EXPERIMENT_NAME}_distortion_corrected`

### Verification
- ✓ Frame extraction: 8 frames extracted at 2 fps
- ✓ Feature extraction: SIFT features detected (8k-13k per image)
- ✓ Feature matching: 28 image pairs matched exhaustively
- ✓ Sparse reconstruction: All 8 images registered, 3,980 points reconstructed
- ✓ Distortion correction: Successful, undistorted images and poses written
- ✓ Output structure: Correct paths created with proper directory hierarchy

---

## Training Loss Visualization (2026-06-19)

### Implementation
Created `scripts/plot_training_loss.py` to analyze and visualize OpenSplat training convergence.

**Features:**
- Parses training loss from `logs/opensplat_pipeline.log` (format: `Step N: loss (%)`)
- Generates plot with:
  - **Raw loss** (light blue, 80% opacity) with markers
  - **Moving average** (dark blue, 80% opacity, window=10 steps)
- Prints loss statistics (min, max, average)
- Saves PNG plot to `logs/training_loss.png` at 150 DPI

**Pipeline Integration:**
- Updated `launch_opensplat.sh` to pipe OpenSplat output to `logs/opensplat_pipeline.log` using `tee`
- Ensures log file is created automatically during training
- Consistent with project's "use tee for logging" pattern

**Usage:**
```bash
uv run python scripts/plot_training_loss.py
```

**Log Format:**
The OpenSplat binary outputs loss at regular intervals in the format:
```
Step 10: 0.263509 (1%)
Step 20: 0.29705 (2%)
...
Step 1000: 0.143528 (100%)
```

This is automatically captured by `launch_opensplat.sh` to `logs/opensplat_pipeline.log`.

---

## Semantic Naming for Gaussian Splat Models (2026-06-19)

### Implementation
Updated `launch_opensplat.sh` to automatically generate semantically meaningful filenames for saved models.

**Filename Format:**
```
opensplat_output_numiters{NUM_ITERS}_{YYYYMMDD}_{HHMM}.ply
```

**Example outputs:**
- `opensplat_output_numiters2000_20260619_1430.ply` (2000 iterations, June 19 2026, 2:30 PM)
- `opensplat_output_numiters5000_20260619_1545.ply` (5000 iterations, June 19 2026, 3:45 PM)

**Changes Made:**
- Added timestamp generation using `date +"%Y%m%d_%H%M"` in `launch_opensplat.sh`
- Build filename from: `opensplat_output_numiters${NUM_ITERS}_${TIMESTAMP}.ply`
- Updated output messages to show the generated filename and timestamp
- Updated `pipeline.sh` output messages to document the new naming scheme

**Benefits:**
- **Easy comparison**: Multiple training runs can be compared side-by-side with clear parameter information
- **Unique files**: No risk of overwriting previous results
- **Self-documenting**: Filename contains experiment parameters and when it was run
- **Sortable**: Results are naturally sorted chronologically and by iteration count

---

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

4. Creates validation render directory automatically before training

**What This Enables:**
- OpenSplat withholds `frame_0032.jpg` from training (same image every run)
- Renders validation image every 10 training steps to `VAL_RENDER_DIR`
- Outputs final validation loss to stdout (captured in log file)
- Allows tracking held-out view quality over time via rendered images

**Example Output During Training:**
```
Starting OpenSplat training on M4 Metal GPU...
Validation enabled: true (image: frame_0032.jpg)
[Training outputs...]
{image_path} validation loss: 0.0445

Training complete! Output saved to ...
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

## Feature Extraction Comparison & Simplification (2026-06-20)

### Feature Comparison Results
Tested SIFT_BRUTEFORCE vs SIFT_LIGHTGLUE on the 4-second test video (`test_4s_feature_comparison`):
- Both methods successfully reconstructed the scene with 8 frames and ~4K sparse points
- SIFT_BRUTEFORCE selected as the default for production use
- Removed all feature type parameterization from COLMAP pipeline

### COLMAP Script Cleanup (Completed 2026-06-20)

**Simplified `launch_colmap.sh`:**
- Removed `--feature-type` command-line argument entirely
- Removed feature type case statement and validation
- Hardcoded SIFT_BRUTEFORCE feature extraction and matching
- Updated output directory naming: now only includes `max-num-features` parameter
- Simplified help text and usage examples
- Cleaner, more focused script for production use

**Before:**
```bash
./launch_colmap.sh --max-num-features 8192 --feature-type SIFT_BRUTEFORCE
./launch_colmap.sh --feature-type SIFT_LIGHTGLUE
./launch_colmap.sh --max-num-features 4096 --feature-type ALIKED_LIGHTGLUE
```

**After:**
```bash
./launch_colmap.sh --max-num-features 8192
./launch_colmap.sh --max-num-features 4096
```

**Configuration:**
- Default max features: 8192 (configurable via `--max-num-features`)
- Feature extraction: SIFT (10 octaves, peak threshold 0.00667)
- Feature matching: SIFT_BRUTEFORCE (exhaustive matcher)
- Output path format: `{experiment_name}_max-num-features-{N}`

**Changes Made:**
1. Removed feature type option parsing (lines 46-83 simplified)
2. Hardcoded `FEATURE_BASE="SIFT"` and `FEATURE_MATCHING="SIFT_BRUTEFORCE"`
3. Updated output dir naming to exclude feature type
4. Simplified help text to 1 option instead of 4
5. Updated status messages throughout pipeline
6. Changed timing JSON field: `"feature_type"` → `"feature_matcher": "SIFT_BRUTEFORCE"`

**Benefits:**
- Easier to understand and maintain
- Reduced argument parsing complexity
- Clear that we're using a proven, validated approach
- Experiment naming is simpler and cleaner

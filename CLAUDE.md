
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

### Loop Detection Experiment (2026-06-20)

**Status**: Completed with Important Finding

**What was implemented:**
1. **Enhanced `launch_colmap.sh`** with vocabulary tree-based loop detection support
   - Added `--loop-detection` flag to enable place recognition via pre-built vocabulary tree
   - Added `--vocab-tree` parameter for custom vocabulary tree paths
   - Uses Flickr100K 32K-word vocabulary tree (15MB) for loop closure detection

2. **Created `run_loop_detection_experiment.sh`** to automate comparison pipeline
   - Runs sequential matcher with and without loop detection
   - Times each COLMAP and OpenSplat stage separately
   - Generates comprehensive timing report

**Issues Fixed:**
- ✓ (2026-06-20 19:02) **Double-quoted vocabulary tree path** - Removed escaped quotes in line 230
- ✓ (2026-06-20 19:07) **Vocabulary tree format incompatibility** - DISCOVERED

**Critical Issue Found: Vocabulary Tree Format Incompatibility**

**Problem**:
- The available vocabulary tree (`vocab_tree_flickr100K_words32K.bin`) is in **legacy flann-based format**
- COLMAP switched from flann to faiss indices in **May 2025**
- Current COLMAP version cannot read the legacy format file
- Result: `--loop-detection` parameter fails when trying to load the vocab tree

**Error Message**:
```
Failed to read faiss index. This may be caused by reading a legacy flann-based index,
because COLMAP switched from flann to faiss in May 2025.
```

**Impact**:
- Stage 1 (sequential matching WITHOUT loop detection): ✅ **SUCCEEDS**
- Stage 2 (sequential matching WITH vocab tree loop detection): ❌ **FAILS**

**Why Stage 1 Works**:
The sequential matcher already has built-in loop detection via `--SequentialMatching.quadratic_overlap 1`, which:
- Matches each frame with nearby frames (overlap parameter)
- Also matches with exponentially-spaced frames to detect loops
- Does NOT require the vocabulary tree file

**Options to Fix**:
1. **Build new faiss-based vocabulary tree** (requires data)
   - Use: `colmap vocab_tree_builder` command available
   - Need training images with known loop points
   - Time investment: high

2. **Accept current approach** (recommended)
   - Sequential matching with quadratic overlap already provides loop detection
   - No vocabulary tree dependency
   - Faster, simpler, works with available data

3. **Upgrade vocabulary tree from flann to faiss**
   - COLMAP commit c7a58462b813e406c304a9dafb475b87036924cf has upgrader tool
   - Would need to check out that specific commit
   - Time investment: moderate

**Recommendation**:
The sequential matcher WITH `quadratic_overlap=1` (already implemented) provides effective loop detection without requiring an external vocabulary tree. The vocabulary tree would be an optimization but is not essential.

**Log Files to Monitor During Loop Detection Experiment:**

1. **Main experiment log** (wrapper):
   - `logs/loop_detection_full.log` - Overall progress and timing

2. **COLMAP logs** (feature extraction, matching, reconstruction):
   - `logs/colmap_loop_detection_full_no_loop_sequential_max-num-features-4096.log` - Without loop detection
   - `logs/colmap_loop_detection_full_with_loop_sequential_max-num-features-4096_loop.log` - With loop detection
   - Check for:
     - "No images with matches" error → indicates matcher failed
     - "Failed to create any sparse model" → reconstruction failed
     - Feature counts per image

3. **OpenSplat logs** (training):
   - `logs/opensplat_pipeline.log` - Training progress, loss values
   - Check for:
     - "Invalid project folder" → data directory structure wrong
     - Loss convergence pattern
     - Memory issues ("CUDA out of memory" or similar)

4. **Timing summary** (JSON):
   - `logs/colmap_timings.jsonl` - Each run's duration with parameters

5. **Final report**:
   - `loop_detection_full_loop_detection_report.md` - Comparison results

**What to Look For:**
- COLMAP stage times: Compare matching speed without vs. with loop detection
- Loop closure matches: Check logs for "loop_detection" keyword to verify it's being used
- OpenSplat training: Ensure both datasets produce valid reconstructions
- Final timing overhead: How much slower is loop detection? Is it worth the improved geometry?

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
  - Extract minimal 8-frame subset from `data/incoming/movies/gardenbed_2026-06-17.mov`
  - Use: `ffmpeg -i data/incoming/movies/gardenbed_2026-06-17.mov -vf "fps=0.2" -q:v 2 data/intermediates/test_8frames/images/frame_%04d.jpg`
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
Successfully tested COLMAP pipeline with 4-second test video extracted from middle of `data/incoming/movies/gardenbed_2026-06-17.mov`:
- Created: `data/incoming/movies/gardenbed_test_4s_middle.mov` (4-second snippet)
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

### COLMAP Configuration (.env)

Added `MAX_NUM_FEATURES` parameter to `.env` for easy configuration:
```bash
# COLMAP Structure-from-Motion
# Max number of SIFT features per image (default: 8192, faster: 2048, quality: 16384)
MAX_NUM_FEATURES=8192
```

**Configuration Options:**
- Set value in `.env` to control default behavior
- Command-line override still available: `./launch_colmap.sh --max-num-features 4096`
- Command-line arguments take precedence over `.env` value
- If neither is set, defaults to 8192 features

**Recommended Values:**
- `2048`: Fast iteration for testing (30s-90s COLMAP time)
- `8192`: Balanced quality/speed for production (13-15 min total)
- `16384`: Maximum quality (may exceed MacBook Air memory)

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

---

## Unified Experiment Workflow (2026-06-20)

### Overview
Refactored the experiment system to simplify running feature matching comparisons. Created a unified COLMAP launcher with matcher parameterization and an experiment orchestrator that automates full COLMAP + OpenSplat comparison runs.

### Files Created

#### 1. **launch_colmap.sh** (Unified COLMAP launcher)
Merged exhaustive and sequential matchers into a single script with `--matcher` parameter.

**Features:**
- Single unified entry point for all COLMAP runs
- Takes `--matcher exhaustive|sequential` to switch strategies
- All parameters overridable via command-line (no .env editing needed)
- Parameters: `--matcher`, `--max-num-features`, `--experiment`, `--video`
- Output directory naming includes matcher type: `{experiment}_{matcher}_max-num-features-{N}`

**Example:**
```bash
./launch_colmap.sh --matcher sequential --max-num-features 4096 --experiment scene --video video.mov
```

#### 2. **run_experiment.sh** (Experiment orchestrator)
Automates full comparison experiments with both COLMAP and OpenSplat.

**Features:**
- Runs COLMAP and OpenSplat for multiple matchers in sequence
- Auto-generates comparison reports
- Temporary .env management to override settings per run
- Parameters: `--name`, `--video`, `--max-features`, `--iters`, `--matchers`

**Example:**
```bash
./run_experiment.sh --name test --video video.mov --iters 500 --matchers exhaustive,sequential
```

### Files Removed/Consolidated

- ✓ `launch_colmap_exhaustive.sh` - Merged into unified `launch_colmap.sh`
- ✓ `launch_colmap_sequential.sh` - Merged into unified `launch_colmap.sh`
- ✓ `launch_opensplat_semantic.sh` - Removed (legacy, replaced by .env-based `launch_opensplat.sh`)
- ✓ `EXPERIMENT_WORKFLOW.md` - Consolidated into README.md
- ✓ `SETUP_COMPLETE.md` - Consolidated into CLAUDE.md (this file)

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
SSIM_WEIGHT=0.5                           # Perceptual loss weight
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
5. **Logging**: All output tee'd to `logs/` directory with semantic names

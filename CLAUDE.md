
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

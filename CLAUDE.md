
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

### OpenSplat Binary Issue (2026-06-18)
**Status**: Blocker - Segmentation fault

When testing `try_bash_opensplat.sh`:
- Binary successfully loads COLMAP sparse data (99,506 points)
- MPS (Metal Performance Shaders) initializes correctly
- Crashes with segmentation fault during model initialization/training
- Root cause: OpenMP library duplication in the binary
  - Error: "OMP: Error #15: Initializing libomp.dylib, but found libomp.dylib already initialized"
  - Multiple copies of OpenMP runtime linked into opensplat binary
  - Workaround (KMP_DUPLICATE_LIB_OK=TRUE) allows startup but leads to segfault

**Next Steps**:
- Rebuild OpenSplat binary without OpenMP duplication (check CMake config)
- Consider using system OpenMP instead of bundled version
- Verify Metal GPU support is properly configured

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
1. Path references and data organization bugs prevent pipeline from running
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


## Project info
We will be training and rendering a 3D Gaussian splat. The language will be python, with env managed with uv. The development and compute will happen on this macbook air M4 24GB laptop.

## Project Goal
We will be attempting to create a 3D gaussian splat from extracted frames and structure from motion (`data/intermediate/frames` and `data/intermediate/sfm`). The computation will be happening on a macbook air M4 24gb. We will use opensplat to initialize and train the 3D gaussian splat (`https://github.com/pierotofy/opensplat`).

## Workflow info
Please keep your plan, next steps, debugging notes, and other documentation for yourself in this file, CLAUDE.md.
For other materials, e.g. run instructions, and other project info, maintain documentation in README.md

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

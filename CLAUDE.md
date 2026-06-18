
## Project info
We will be training and rendering a 3D Gaussian splat. The language will be python, with env managed with uv. The development and compute will happen on this macbook air M4 24GB laptop.

## Workflow info
Please keep your plan, next steps, debugging notes, and other documentation for yourself in this file, CLAUDE.md.
For other materials, e.g. run instructions, and other project info, maintain documentation in README.md

## Inner and outer repo organization for rapid prototyping
Notice there is an inner project repo named gsplat-mlx pasted into the project. Avoid modifying this repository unless absolutely necessary. We will do our work in the outer repository. The inner project, gsplat-mlx, is expected to be a key dependency and it's simpler to have its code available here in the repo where we can use it heavily with ease.

## Experiments
Use tee to pipe console output to the `logs` directory.

---

## Training Script Implementation (2026-06-18)

### What was created:
1. **config.toml** - Configuration file with training parameters
   - Data paths for frames and SfM camera poses
   - Training hyperparameters (learning rates, number of steps, Gaussian count)
   - Image downscaling for memory efficiency
   - Output directory for trained model

2. **scripts/train_gaussian_splat.py** - Complete training script
   - Loads frames from `data/intermediate/frames/`
   - Loads camera intrinsics and poses from `data/intermediate/sfm/`
   - Implements differentiable rendering using gsplat-mlx's low-level accumulate path
   - Full training loop with Adam-style optimization
   - Saves checkpoints and final model as PLY format

### Key design decisions:
- Uses **differentiable accumulate path** (not tile-based rasterizer) for full gradient support
- Supports **per-image training** (processes one random view per step)
- Downscaling option to handle large images on memory-constrained machines
- Compatible with M4 MacBook Air (Metal acceleration via MLX)

### Issues encountered:
- **GPU memory issues** with high-resolution images and large Gaussian counts
  - Addressed with downscaling (4-8x) and reduced Gaussian counts (100-500)
- **GPU address faults** in gsplat-mlx accumulate function (investigating)
  - Even simple_trainer example fails with same error
  - Suggests MLX/Metal compatibility issue, not script issue

### Next steps for debugging:
1. Test if issue is specific to this Mac hardware or MLX version
2. Check if gsplat-mlx needs update or has known Metal issues
3. Try alternative approaches (torch-based 3DGS, COLMAP integration)
4. Enable more verbose MLX logging to identify GPU fault location

### Usage:
```bash
uv run python scripts/train_gaussian_splat.py --config config.toml --output data/intermediate/gs/latest
```

### Configuration notes:
- Adjust `downscale` factor in config.toml if GPU errors occur
- Reduce `num_gaussians` and `num_steps` for testing on limited memory
- Current defaults are conservative for 24GB M4 MacBook Air
# iPhone Video to 3D Gaussian Splat

Convert iPhone video recordings into 3D Gaussian Splat models on macOS using OpenSplat.

## Overview

This project implements a two-stage pipeline to convert iPhone video into 3D Gaussian Splat models:

1. **COLMAP SfM Processing** (`current_scene/` → `current_scene_distortion_corrected/`)
   - Extract frames from video
   - Compute camera poses and 3D points using SfM
   - Linearize camera distortion models via `colmap image_undistorter`

2. **Gaussian Splat Training** (`current_scene_distortion_corrected/opensplat_output/`)
   - Train a 3D Gaussian Splat model using OpenSplat with distortion-corrected data

The pipeline is optimized to run on Apple Silicon (M-series) Macs.

### Key Features
- **Video frame extraction** from iPhone video files
- **COLMAP SfM reconstruction** for camera pose estimation
- **3D Gaussian Splat training** with differentiable rendering
- **Apple Silicon support** for M-series Macs
- **Memory-efficient** downscaling for MacBook Air compatibility

## Project Structure

```
.
├── README.md                          # This file
├── CLAUDE.md                          # Development notes & workflow
├── config.toml                        # Training configuration
├── main.py                            # Main entry point
├── pyproject.toml                     # Python project configuration
├── scripts/
│   └── train_gaussian_splat.py        # Main training script
├── opensplat/                         # OpenSplat dependency (embedded)
│   └── ...
├── colmap/                            # COLMAP dependency (embedded)
│   └── ...
├── data/
│   ├── incoming/
│   │   └── *.MOV                      # Input iPhone video files
│   └── intermediates/
│       ├── current_scene/             # [COLMAP Stage 1] Raw SfM reconstruction
│       │   ├── images/                # Extracted video frames
│       │   ├── database.db            # COLMAP feature database
│       │   └── sparse/                # COLMAP SfM output
│       │       └── 0/
│       │           ├── cameras.bin
│       │           ├── images.bin
│       │           └── points3D.bin
│       └── current_scene_distortion_corrected/  # [COLMAP Stage 2 & OpenSplat] Distortion-corrected data
│           ├── images/                # Undistorted frames
│           ├── sparse/                # Undistorted camera poses
│           │   └── 0/
│           │       ├── cameras.bin
│           │       ├── images.bin
│           │       └── points3D.bin
│           └── opensplat_output/      # [OpenSplat] Trained models
│               └── *.ply              # Gaussian Splat models
└── src/                               # Source code utilities
```

## Prerequisites

- macOS with Apple Silicon (M1/M2/M3/M4 or later)
- Python 3.9+
- COLMAP installed (`brew install colmap`)
- At least 16GB RAM (24GB recommended)
- Disk space for video frames and models (~10-50GB depending on video length)

## Installation

1. **Clone the repository and install dependencies:**
   ```bash
   uv sync
   ```

2. **Verify COLMAP is installed:**
   ```bash
   which colmap
   ```

## Configuration

Before running the pipeline, configure the project by editing `.env`:

```bash
# .env
PROJECT_DIR="/Users/bc/brendanchambers/2026-06-18-iphone-video-to-splat"
VIDEO_PATH="./data/incoming/gardenbed_2026-06-17.MOV"
EXPERIMENT_NAME="current_scene"
```

- `PROJECT_DIR`: Absolute path to the project directory
- `VIDEO_PATH`: Relative path to input video from `PROJECT_DIR`
- `EXPERIMENT_NAME`: Name for this experiment (used for output directory naming)

## Usage

The pipeline consists of two main stages. All intermediate data is stored in `data/intermediates/`. Both stages use `.env` for configuration.

### Stage 1: COLMAP SfM Processing

Extract frames from the iPhone video, compute camera poses using SfM, and linearize distortion models.

Run the automated script:

```bash
bash try_bash_colmap.sh
```

This script will:
1. Extract frames at 2 fps from the video specified in `.env`
2. Run COLMAP feature extraction with RADIAL distortion model
3. Perform exhaustive feature matching
4. Compute Structure-from-Motion reconstruction
5. Linearize camera distortion and undistort frames for OpenSplat

**Output**:
- `data/intermediates/current_scene/sparse/0/` - Raw SfM reconstruction
- `data/intermediates/current_scene_distortion_corrected/images/` - Undistorted frames
- `data/intermediates/current_scene_distortion_corrected/sparse/0/` - Distortion-corrected camera poses

### Stage 2: OpenSplat Training

Train a 3D Gaussian Splat model using the distortion-corrected data from Stage 1:

```bash
bash try_bash_opensplat.sh
```

This script will:
1. Load camera poses and 3D points from COLMAP output
2. Load distortion-corrected frames
3. Initialize 3D Gaussians from the sparse point cloud
4. Run training on Apple Metal GPU for 2000 iterations
5. Save the trained model as PLY format

**Output**: `data/intermediates/{EXPERIMENT_NAME}_distortion_corrected/opensplat_output/scene.ply`

### Training Configuration

The `try_bash_opensplat.sh` script is configured for rapid iteration on the M4 MacBook Air with 2000 training steps. For production use, adjust the training parameters directly in the script (line 23):

```bash
$OPENSPLAT_BIN "$DATA_DIR" \
  --colmap-image-path "$IMAGES_DIR" \
  --output "$OUTPUT_DIR/scene.ply" \
  --num-iters 2000          # Increase for better quality
```

Additional flags for optimization:
- `--downscale-factor 2`: Scale images down by 2x for memory efficiency
- `--num-downscales 3`: Progressive resolution schedule
- `--ssim-weight 0.2`: Balance between SSIM and L1 loss
- `--densify-grad-thresh 0.0002`: Gaussian splitting sensitivity
- `--sh-degree 3`: Spherical harmonics degree (higher = more detail)

## Known Issues

### Memory Constraints
Large images and high Gaussian counts can cause memory errors. Use the `downscale` parameter to reduce image resolution before training.

## Future Work

- [ ] Add real-time viewer for trained models
- [ ] Support for batch video processing
- [ ] Optimize memory usage for longer videos
- [ ] Add camera trajectory visualization
- [ ] Performance benchmarking on different M-series chips
- [ ] Integration with alternative 3DGS implementations

## Dependencies

- **opensplat**: Gaussian splat implementation (embedded in repo)
- **colmap**: Structure-from-Motion reconstruction
- **ffmpeg**: Video frame extraction
- **Python**: 3.9+

## Contributing

For development notes and workflow information, see `CLAUDE.md`.

## References

- [OpenSplat](https://github.com/antimatter15/splat)
- [COLMAP](https://colmap.github.io/)
- [3D Gaussian Splatting Paper](https://repo.cvpr.org/)

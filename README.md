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
- COLMAP cloned into top level of project
- OpenSplat cloned into top level of project
- At least 16GB RAM (24GB recommended)
- Disk space for video frames and models (~10-50GB depending on video length)

## Setup

Build COLMAP and OpenSplat. Update .env to configure your run.

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
bash launch_colmap.sh
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
bash launch_opensplat.sh
```

This script will:
1. Load camera poses and 3D points from COLMAP output
2. Load distortion-corrected frames
3. Initialize 3D Gaussians from the sparse point cloud
4. Run training on Apple Metal GPU for 2000 iterations
5. Save the trained model as PLY format

**Output**: `data/intermediates/{EXPERIMENT_NAME}_distortion_corrected/opensplat_output/scene.ply`

### Training Configuration

The `launch_opensplat.sh` script uses the `NUM_ITERS` value from `.env`. For production use, adjust the training parameters in `.env` or directly in the script:

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

## Visualization

### Feature Extraction Visualization

Visualize SIFT features extracted by COLMAP on each frame. Shows the 500 strongest features with optional orientation indicators:

```bash
uv run python scripts/visualize_colmap_features.py \
  --colmap-dir data/intermediates/test_4s \
  --output-dir data/intermediates/test_4s/annotated_images \
  --max-features 500 \
  --show-orientation
```

**Options:**
- `--max-features N`: Show only the N strongest features (default: all)
- `--show-orientation`: Draw orientation lines for each feature
- `--circle-radius R`: Radius of feature circles in pixels (default: 5)
- `--line-length L`: Length of orientation lines in pixels (default: 8)

**Output**: Annotated images with green circles marking feature locations, blue lines showing orientation angles.

### Feature Matching Visualization

Visualize feature correspondences between image pairs from COLMAP exhaustive matching. Shows the 5 strongest matches with random colors:

```bash
uv run python scripts/visualize_feature_matches.py \
  --colmap-dir data/intermediates/test_4s \
  --output-dir data/intermediates/test_4s/match_visualizations \
  --max-pairs 28 \
  --max-matches 5
```

**Options:**
- `--max-pairs N`: Visualize first N image pairs (default: all)
- `--max-matches M`: Show only the M strongest feature matches per pair (default: 5)

**Output**: Side-by-side image pairs with:
- **Blue bounding box** around first image
- **Orange bounding box** around second image
- **Colored match lines** connecting corresponding features
- **Semi-transparent images** (50% opacity) to highlight match lines

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

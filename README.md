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

## Usage

The pipeline consists of two main stages. All intermediate data is stored in `data/intermediates/`.

### Stage 1: COLMAP SfM Processing

Extract frames from the iPhone video, compute camera poses using SfM, and linearize distortion models.

A complete script is available in `try_bash_colmap.sh` (from previous development). However, the script has path bugs that need fixing. For now, run the steps manually:

```bash
# Setup
EXPERIMENT_NAME="current_scene"
PROJECT_DIR=$(pwd)
IMAGES_DIR="$PROJECT_DIR/data/intermediates/$EXPERIMENT_NAME/images"
SPARSE_DIR="$PROJECT_DIR/data/intermediates/$EXPERIMENT_NAME/sparse"
DATABASE_PATH="$PROJECT_DIR/data/intermediates/$EXPERIMENT_NAME/database.db"

mkdir -p "$IMAGES_DIR"
mkdir -p "$SPARSE_DIR"

# Extract frames from iPhone video
ffmpeg -i data/incoming/video.MOV -vf "fps=2" -q:v 2 "$IMAGES_DIR/frame_%04d.jpg"

# Extract SIFT features
colmap feature_extractor \
  --database_path "$DATABASE_PATH" \
  --image_path "$IMAGES_DIR" \
  --ImageReader.camera_model "RADIAL" \
  --ImageReader.single_camera 1

# Match features between images
colmap exhaustive_matcher \
  --database_path "$DATABASE_PATH"

# Run Structure-from-Motion reconstruction
colmap mapper \
  --database_path "$DATABASE_PATH" \
  --image_path "$IMAGES_DIR" \
  --output_path "$SPARSE_DIR"

# Linearize distortion and undistort frames
mkdir -p "$PROJECT_DIR/data/intermediates/${EXPERIMENT_NAME}_distortion_corrected"

colmap image_undistorter \
  --image_path "$IMAGES_DIR" \
  --input_path "$SPARSE_DIR/0" \
  --output_path "$PROJECT_DIR/data/intermediates/${EXPERIMENT_NAME}_distortion_corrected" \
  --output_type COLMAP
```

**Output**:
- `data/intermediates/current_scene/sparse/0/` - Raw SfM reconstruction
- `data/intermediates/current_scene_distortion_corrected/images/` - Undistorted frames
- `data/intermediates/current_scene_distortion_corrected/sparse/0/` - Distortion-corrected camera poses

### Stage 2: OpenSplat Training

Train a 3D Gaussian Splat model using the distortion-corrected data.

```bash
mkdir -p data/intermediates/current_scene_distortion_corrected/opensplat_output

uv run python scripts/train_gaussian_splat.py \
  --images_path data/intermediates/current_scene_distortion_corrected/images \
  --sfm_path data/intermediates/current_scene_distortion_corrected/sparse/0 \
  --output data/intermediates/current_scene_distortion_corrected/opensplat_output/model.ply
```

**Configuration options** (edit `config.toml`):
- `downscale`: Image downscaling factor (2-8x for memory efficiency)
- `num_gaussians`: Number of Gaussians to train (100-10000)
- `num_steps`: Training iterations (5000-50000)
- `learning_rate`: Initial learning rate for optimizer

## Configuration

The `config.toml` file contains training hyperparameters for Stage 3 (OpenSplat training):

```toml
[training]
num_gaussians = 500
num_steps = 10000
learning_rate = 0.001
downscale = 4
```

Adjust these values based on your hardware:
- **24GB M4 MacBook Air**: `downscale=4`, `num_gaussians=500-1000`
- **16GB M3 MacBook Air**: `downscale=8`, `num_gaussians=100-300`
- **Higher-end Macs**: Can increase `num_gaussians` and reduce `downscale`

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

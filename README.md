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
│   │   └── movies/
│   │       └── *.MOV                  # Input iPhone video files
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
VIDEO_PATH="./data/incoming/movies/gardenbed_2026-06-17.mov"
EXPERIMENT_NAME="current_scene"

# COLMAP Structure-from-Motion
MAX_NUM_FEATURES=8192

# OpenSplat Training
NUM_ITERS=1500
```

**Configuration Parameters:**
- `PROJECT_DIR`: Absolute path to the project directory
- `VIDEO_PATH`: Relative path to input video from `PROJECT_DIR`
- `EXPERIMENT_NAME`: Name for this experiment (used for output directory naming)
- `MAX_NUM_FEATURES`: Max SIFT features per image (default: 8192, faster: 2048, quality: 16384)
- `NUM_ITERS`: Number of OpenSplat training iterations (default: 1500)

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

All output is logged to `logs/colmap_pipeline.log`.

**Output**:
- `data/intermediates/current_scene/sparse/0/` - Raw SfM reconstruction
- `data/intermediates/current_scene_distortion_corrected/images/` - Undistorted frames
- `data/intermediates/current_scene_distortion_corrected/sparse/0/` - Distortion-corrected camera poses
- `logs/colmap_pipeline.log` - Detailed pipeline execution log

### Stage 2: OpenSplat Training

Train a 3D Gaussian Splat model using the distortion-corrected data from Stage 1:

```bash
bash launch_opensplat.sh
```

This script will:
1. Load camera poses and 3D points from COLMAP output
2. Load distortion-corrected frames
3. Initialize 3D Gaussians from the sparse point cloud
4. Run training on Apple Metal GPU for configured iterations
5. Save the trained model as PLY format

All training output is logged to `logs/opensplat_pipeline.log`.

**Outputs**:
- `data/intermediates/{EXPERIMENT_NAME}_distortion_corrected/opensplat_output/scene.ply` - Trained Gaussian Splat model
- `logs/opensplat_pipeline.log` - Training log with loss values at each step (used for visualization)

### Running the Full Pipeline

To run both stages sequentially, use the unified pipeline script:

```bash
bash pipeline.sh
```

This will:
1. Execute the COLMAP SfM stage (Stage 1)
2. Upon successful completion, execute the OpenSplat training stage (Stage 2)

Pipeline logs:
- `logs/colmap_pipeline.log` - COLMAP stage output
- `logs/opensplat_pipeline.log` - OpenSplat training output

If either stage fails, the pipeline stops and reports the error to help with debugging.

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
  --max-features 2000 \
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
uv run python scripts/visualize_colmap_feature_matches.py \
  --colmap-dir data/intermediates/test_4s \
  --output-dir data/intermediates/test_4s/match_visualizations \
  --max-pairs 10 \
  --max-matches 25
```

**Options:**
- `--max-pairs N`: Visualize first N image pairs (default: all)
- `--max-matches M`: Show only the M strongest feature matches per pair (default: 5)

**Output**: Side-by-side image pairs with:
- **Blue bounding box** around first image
- **Orange bounding box** around second image
- **Colored match lines** connecting corresponding features
- **Semi-transparent images** (50% opacity) to highlight match lines

### Training Loss Visualization

Analyze the training loss curve from OpenSplat training. The script parses `logs/opensplat_pipeline.log` and generates a plot with both raw and smoothed loss values:

```bash
uv run python scripts/plot_training_loss.py
```

**Output**: `logs/training_loss.png` showing:
- **Light blue line** with markers: Raw training loss at each step (80% opacity)
- **Dark blue line**: Moving average (window size: 10 steps) for trend visualization (80% opacity)
- **Statistics printed**: Min, max, and average loss values

The log file is automatically created by `launch_opensplat.sh` during training with the format:
```
Step 10: 0.263509 (1%)
Step 20: 0.29705 (2%)
...
Step 1000: 0.143528 (100%)
```

This visualization helps identify training convergence and detect potential overfitting or instability in the Gaussian Splat optimization.

## Experimental Results: COLMAP Feature Parameter Sweep

A comprehensive parameter sweep was conducted on a full 62-second iPhone video (gardenbed scene, 124 frames at 2 fps) to evaluate the impact of COLMAP's `max_num_features` parameter on reconstruction quality and training time.

### Methodology

- **Dataset**: Full `gardenbed_2026-06-17.mov` (62 seconds, 1920×1080 iPhone video)
- **COLMAP Parameters Tested**: 256, 2048, and 8192 features
- **Training Steps**: 1500 and 5000 iterations for each parameter
- **Hardware**: M4 MacBook Air 24GB RAM
- **Validation**: Held-out test image (frame_0032.jpg) validation loss

### Results Summary

#### COLMAP Stage (SfM Reconstruction)

| max_num_features | COLMAP Time | Images Registered | Sparse Points |
|------------------|-------------|-------------------|---------------|
| 256 | 29.99s | 75/124 (60%) | ~29k |
| 2048 | 93.59s | 124/124 (100%) | ~115k |
| 8192 | 807.71s | 124/124 (100%) | ~200k |

**Key Finding**: max_num_features=256 fails to register all frames (~60% coverage), while both 2048 and 8192 achieve complete scene reconstruction.

#### OpenSplat Training (1500 iterations)

| Parameter | Time | Val Loss | Gaussians | Quality Score |
|-----------|------|----------|-----------|---------------|
| 256 | 80.81s | 0.244 | 3,908 | 1.0x |
| 2048 | 107.36s | 0.170 | 52,921 | 1.43x |
| 8192 | 166.84s | 0.125 | 163,764 | 1.95x |

#### OpenSplat Training (5000 iterations)

| Parameter | Time | Val Loss | Improvement | Quality Score |
|-----------|------|----------|-------------|---------------|
| 256 | 698.37s | 0.171 | ↓30% | 1.42x |
| 2048 | 963.15s | 0.134 | ↓21% | 1.82x |
| 8192 | 990.08s | 0.118 | ↓5.6% | 2.07x |

### Interpretation

**Validation Loss Convergence:**
- **256 features**: Significant improvements from 1500→5000 iters (0.244 → 0.171, -30%)
- **2048 features**: Strong improvements from 1500→5000 iters (0.170 → 0.134, -21%)
- **8192 features**: Diminishing returns from 1500→5000 iters (0.125 → 0.118, -5.6%)

**Practical Implications:**
- **256 features** is unsuitable for complex scenes (60% frame registration) but trains quickly
- **2048 features** provides excellent balance: 100% registration + 21% quality improvement with 5000 iters
- **8192 features** offers best reconstruction quality but shows near-saturation at 1500 iters

### Recommendations by Use Case

**Quick Prototyping** (< 2 minutes total):
- Use: max_num_features=256 + 1500 OpenSplat iters
- Note: Only works for simple scenes with continuous camera motion

**Development / Production Balanced** (< 20 minutes total):
- Use: max_num_features=2048 + 5000 OpenSplat iters
- Achieves 2x COLMAP time vs 256, but quality improves 1.82x
- **Recommended for most use cases**

**Maximum Quality**:
- Use: max_num_features=8192 + 5000 OpenSplat iters
- Best reconstruction fidelity for complex dynamic scenes
- ~16.5 minutes total pipeline time on M4 MacBook Air

### Parameter Sweep Implementation

The pipeline supports parameterized testing via:

**Method 1: Configuration File (.env)**
```bash
# Edit .env to set default
MAX_NUM_FEATURES=2048

# Run pipeline
bash launch_colmap.sh
```

**Method 2: Command-Line Override**
```bash
# Override .env setting via command-line
bash launch_colmap.sh --max-num-features 4096

# Semantic output naming
# Creates: data/intermediates/EXPERIMENT_NAME_max-num-features-4096/
```

Timing results are automatically logged to `logs/colmap_timings.jsonl` and `logs/opensplat_timings.jsonl` in JSON Lines format for analysis.

## Known Issues

### Memory Constraints
Large images and high Gaussian counts can cause memory errors. Use the `downscale` parameter to reduce image resolution before training.

## Future Work Suggestions

- [ ] Save validation images to the appropriate experiment directory during training
- [ ] Render validaiton images less frequently if needed
- [ ] Check validation loss throughout training, not just at the end
- [ ] Add real-time viewer for trained models
- [ ] Support for batch video processing
- [ ] Tune memory usage and running time
- [ ] Add camera trajectory visualization
- [ ] Performance benchmarking on different M-series chips
- [ ] Integration with alternative 3DGS implementations
- [ ] Compare neural models to classical models (which is the research motivation for the existence of this repo, intended as an approachable baseline representing typical local macbook use)

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
- [COLMAP direct to docs](https://colmap.github.io/faq.html)
- [3D Gaussian Splatting Paper](https://repo.cvpr.org/)

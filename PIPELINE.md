# Python Pipeline for 3D Gaussian Splat Training

This document describes the new Python-based pipeline that replaces the bash scripts for training 3D Gaussian splats from video.

## Overview

The pipeline consists of:
- **Configuration Management**: Hydra + OmegaConf for centralized, composable configuration
- **Modular Utilities**: Separate Python modules for each pipeline step
- **Main Orchestrator**: `pipeline.py` that coordinates the entire workflow

## Architecture

```
pipeline.py                    # Main orchestrator
├── src/
│   ├── frame_extractor.py           # Video → frames (ffmpeg)
│   ├── colmap_feature_extractor.py  # Images → SIFT features
│   ├── colmap_feature_matcher.py    # Match features between frames
│   ├── colmap_mapper.py             # Sparse reconstruction
│   ├── colmap_undistorter.py        # Undistort images & correct cameras
│   └── opensplat_trainer.py         # Train 3D Gaussian splat
└── config/
    └── config.yaml                   # Hydra configuration (replaces .env)
```

## Configuration

All configuration is managed through `config/config.yaml` using Hydra + OmegaConf.

### Key Configuration Sections

**Project paths:**
```yaml
project:
  dir: "/Users/bc/brendanchambers/2026-06-18-iphone-video-to-splat"
  video_path: "./data/incoming/movies/gardenbed_2026-06-17.mov"
  experiment_name: "testing"
```

**Frame extraction:**
```yaml
frame_extraction:
  fps: 2
  use_mpdecimate: true
  mpdecimate_hi: 64
  mpdecimate_lo: 5
  quality: 2
```

**COLMAP parameters:** (feature_extraction, feature_matching, mapper, undistorter)
```yaml
colmap:
  feature_extraction:
    sift_max_num_features: 4096
    # ... more parameters
  feature_matching:
    sequential_overlap: 20
    # ... more parameters
  # etc.
```

**OpenSplat parameters:**
```yaml
opensplat:
  num_iters: 1500
  downscale_factor: 1
  sh_degree: 3
  ssim_weight: 0.2
  # ... more parameters
```

**Validation:**
```yaml
validation:
  enabled: true
  image: "frame_0032.jpg"
```

## Usage

### Running the Full Pipeline

```bash
uv run python pipeline.py
```

This runs all 6 steps:
1. Frame extraction
2. Feature extraction
3. Feature matching
4. Sparse reconstruction
5. Image undistortion
6. Splat training

### Testing the Pipeline

```bash
uv run python test_pipeline.py
```

This validates:
- Configuration loading
- Pipeline instantiation
- Module imports
- Parameter coverage
- Pipeline methods
- Directory structure

### Overriding Configuration

Use Hydra's command-line overrides:

```bash
# Change number of iterations
uv run python pipeline.py opensplat.num_iters=3000

# Use different experiment name
uv run python pipeline.py project.experiment_name=new_experiment

# Change video input
uv run python pipeline.py project.video_path="./path/to/video.mov"

# Disable validation
uv run python pipeline.py validation.enabled=false

# Change frame extraction FPS
uv run python pipeline.py frame_extraction.fps=3
```

## Module Reference

### frame_extractor.py

Extracts frames from video using ffmpeg.

```python
from src.frame_extractor import extract_frames

success = extract_frames(
    video_path=Path("video.mov"),
    output_dir=Path("frames/"),
    use_mpdecimate=True,
    config=config,
    log_file=Path("logs/extraction.log")
)
```

**Parameters:**
- `video_path`: Path to input video
- `output_dir`: Directory for extracted frames
- `use_mpdecimate`: Use intelligent frame selection (default: True)
- `fps`: Fixed FPS if not using mpdecimate
- `config`: OmegaConf config object

### colmap_feature_extractor.py

Extracts SIFT features from images using COLMAP.

```python
from src.colmap_feature_extractor import extract_features

success = extract_features(
    database_path=Path("database.db"),
    image_path=Path("frames/"),
    config=config,
    log_file=Path("logs/colmap.log")
)
```

### colmap_feature_matcher.py

Matches features between frames using sequential matching.

```python
from src.colmap_feature_matcher import match_features

success = match_features(
    database_path=Path("database.db"),
    config=config,
    log_file=Path("logs/colmap.log")
)
```

### colmap_mapper.py

Performs sparse 3D reconstruction.

```python
from src.colmap_mapper import sparse_reconstruction

success = sparse_reconstruction(
    database_path=Path("database.db"),
    image_path=Path("frames/"),
    output_path=Path("sparse/"),
    config=config,
    log_file=Path("logs/colmap.log")
)
```

### colmap_undistorter.py

Undistorts images and corrects camera distortion.

```python
from src.colmap_undistorter import undistort_images

success = undistort_images(
    image_path=Path("frames/"),
    input_model_path=Path("sparse/0"),
    output_path=Path("distortion_corrected/"),
    config=config,
    log_file=Path("logs/colmap.log")
)
```

### opensplat_trainer.py

Trains 3D Gaussian splat using OpenSplat.

```python
from src.opensplat_trainer import train_splat

success = train_splat(
    sparse_model_path=Path("sparse/"),
    images_path=Path("distortion_corrected/images"),
    output_dir=Path("splats/"),
    opensplat_bin=Path("opensplat/build/opensplat"),
    experiment_name="my_experiment",
    config=config,
    log_file=Path("logs/opensplat.log")
)
```

## Logging

All pipeline steps log to:
- **Console**: Real-time output with INFO level
- **File**: Detailed logs in `logs/` directory
  - `logs/pipeline.log`: Main pipeline log
  - `logs/colmap_pipeline.log`: COLMAP steps (extraction, matching, mapping, undistortion)
  - `logs/opensplat_pipeline.log`: OpenSplat training

## Error Handling

Each module function returns a boolean:
- `True`: Step completed successfully
- `False`: Step failed

The pipeline stops on first failure and logs the error. Exception tracebacks are included in logs.

## Comparison with Bash Scripts

| Aspect | Bash Scripts | Python Pipeline |
|--------|-------------|-----------------|
| Configuration | `.env` file + hardcoded paths | Hydra YAML config |
| Parameter overrides | .env editing + bash rerun | Hydra CLI overrides |
| Code organization | Single large scripts | Modular utilities |
| Testing | Manual | Automated test suite |
| Composability | Limited | Full OmegaConf composition |
| Extensibility | Script editing | Module extension |
| IDE support | Limited | Full Python IDE integration |

## Future Enhancements

- [ ] Add validation metrics tracking across runs
- [ ] Implement checkpoint/resume functionality
- [ ] Add multi-experiment comparison utilities
- [ ] Create visualization tools for training progress
- [ ] Add support for custom COLMAP parameter profiles
- [ ] Implement distributed training support

## Integration with Existing Tools

The Python pipeline maintains full compatibility with:
- COLMAP command-line tools (via subprocess)
- OpenSplat binary (via subprocess)
- FFmpeg (via subprocess)
- Existing validation visualization scripts

No modifications to bash scripts are required; they remain available for manual use.

# Loop Detection Comparison Report

This report compares sequential frame matching with and without vocabulary tree-based loop detection.

## Experiment Parameters

Experiment Name: loop_detection_full_fixed
Video: /Users/bc/brendanchambers/2026-06-18-iphone-video-to-splat/data/incoming/movies/gardenbed_2026-06-17.mov
Max Features: 4096
Training Iterations: 1000


## Stage 1: Sequential Matching WITHOUT Loop Detection
COLMAP Time: 69s


## Stage 2: Sequential Matching WITH Loop Detection
COLMAP Time: 11s


## COLMAP Timing Comparison
- Without loop detection: 69s
- With loop detection:    11s
- Difference: -58s (-80.0%)


## Stage 3: OpenSplat Training (WITHOUT Loop Detection)
Training Time: 0s


## Stage 4: OpenSplat Training (WITH Loop Detection)
Training Time: 0s


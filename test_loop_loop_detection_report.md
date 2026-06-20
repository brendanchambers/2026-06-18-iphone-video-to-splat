# Loop Detection Comparison Report

This report compares sequential frame matching with and without vocabulary tree-based loop detection.

## Experiment Parameters

Experiment Name: test_loop
Video: data/incoming/movies/gardenbed_test_4s_middle.mov
Max Features: 4096
Training Iterations: 300


## Stage 1: Sequential Matching WITHOUT Loop Detection
COLMAP Time: 3s


## Stage 2: Sequential Matching WITH Loop Detection
COLMAP Time: 2s


## COLMAP Timing Comparison
- Without loop detection: 3s
- With loop detection:    2s
- Difference: -1s (-30.0%)


## Stage 3: OpenSplat Training (WITHOUT Loop Detection)
Training Time: 0s


## Stage 4: OpenSplat Training (WITH Loop Detection)
Training Time: 0s


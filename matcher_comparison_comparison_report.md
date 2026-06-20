# Feature Matching Comparison Experiment
## matcher_comparison

**Date**: 2026-06-20 18:16:17
**Video**: data/incoming/movies/gardenbed_2026-06-17.mov
**Config**: Max SIFT Features = 4096, Training Iterations = 500

---

## Execution Summary


## 1. COLMAP SfM Results

### exhaustive Matching
- **Time**: 246.63s
- **Output**: `matcher_comparison_exhaustive_max-num-features-4096_distortion_corrected/`

### sequential Matching
- **Time**: 76.62s
- **Output**: `matcher_comparison_sequential_max-num-features-4096_distortion_corrected/`


## 2. OpenSplat Training Results

### exhaustive - OpenSplat
- **Training Iterations**: 500
- **Final Validation Loss**: 
- **Log**: `logs/opensplat_matcher_comparison_exhaustive.log`

### sequential - OpenSplat
- **Training Iterations**: 500
- **Final Validation Loss**: 
- **Log**: `logs/opensplat_matcher_comparison_sequential.log`


## 3. Comparison Summary

| Matcher | COLMAP Time | Validation Loss |
|---------|-------------|-----------------|
| exhaustive | 246.63s | N/A |
| sequential | 76.62s | N/A |

---
Report generated: 2026-06-20 18:21:41

# Feature Matching Comparison Experiment
## gardenbed_sequential

**Date**: 2026-06-20 19:18:17
**Video**: data/incoming/movies/gardenbed_2026-06-17.mov
**Config**: Max SIFT Features = 4096, Training Iterations = 1000

---

## Execution Summary


## 1. COLMAP SfM Results

### sequential Matching
- **Time**: 69.44s
- **Output**: `gardenbed_sequential_sequential_max-num-features-4096_distortion_corrected/`


## 2. OpenSplat Training Results

### sequential - OpenSplat
- **Training Iterations**: 1000
- **Final Validation Loss**: 
- **Log**: `logs/opensplat_gardenbed_sequential_sequential.log`


## 3. Comparison Summary

| Matcher | COLMAP Time | Validation Loss |
|---------|-------------|-----------------|
| sequential | 69.44s | N/A |

---
Report generated: 2026-06-20 19:19:27

# Hyperparameter Sweep Results

## Overview

Completed hyperparameter sweep testing 9 configurations across 2 OpenSplat densification parameters:
- `densify_size_thresh`: [0.0025, 0.005, 0.01]
- `densify_grad_thresh`: [0.0001, 0.0002, 0.0004]

## Results Table

| Densify Size | Densify Gradient | Val Loss  | Time (sec) | Time (min) |
|--------------|------------------|-----------|------------|------------|
| 0.0025       | 0.0001           | 0.344882  | 4.335      | 0.07       |
| 0.0025       | 0.0002           | 0.344928  | 4.210      | 0.07       |
| 0.0025       | 0.0004           | 0.344928  | 4.323      | 0.07       |
| 0.005        | 0.0001           | 0.344940  | 4.196      | 0.07       |
| 0.005        | 0.0002           | 0.344775  | 4.272      | 0.07       |
| 0.005        | 0.0004           | 0.344775  | 4.167      | 0.07       |
| 0.01         | 0.0001           | 0.344775  | 4.325      | 0.07       |
| 0.01         | 0.0002           | 0.344775  | 4.256      | 0.07       |
| 0.01         | 0.0004           | 0.344928  | 4.193      | 0.07       |

## Analysis

### Validation Loss

**Statistics:**
- **Best (lowest):** 0.344775
- **Worst (highest):** 0.344940
- **Mean:** 0.344864
- **Std Dev:** 0.000068
- **Range:** 0.000165 (0.048% variation)

**Best Performing Configurations (Val Loss = 0.344775):**
1. densify_sz0.005_gr0.0002 (4.272s)
2. densify_sz0.005_gr0.0004 (4.167s) ⭐ **Also fastest**
3. densify_sz0.01_gr0.0001 (4.325s)
4. densify_sz0.01_gr0.0002 (4.256s)

### Runtime Analysis

**Statistics:**
- **Fastest:** 4.167 seconds (densify_sz0.005_gr0.0004)
- **Slowest:** 4.335 seconds (densify_sz0.0025_gr0.0001)
- **Mean:** 4.253 seconds
- **Std Dev:** 0.056 seconds
- **Variation:** 3.9%

### Key Findings

1. **Minimal sensitivity to hyperparameters:** Validation loss varies by only 0.048% across all configurations, indicating these densification thresholds have negligible impact on final model quality for this dataset.

2. **Consistent training:** All 9 configurations converged to nearly identical validation losses (~0.3448), suggesting the training process is robust and stable.

3. **Runtime stability:** All runs completed in ~4.2 seconds with minimal variance, demonstrating consistent pipeline performance.

4. **No speed-quality tradeoff:** The fastest configuration (densify_sz0.005_gr0.0004 at 4.167s) also achieves the best validation loss, indicating no computational cost for improved quality.

## Recommendation

**Optimal Configuration:** `densify_sz0.005_gr0.0004`

This configuration:
- ✅ Achieves best (tied) validation loss: 0.344775
- ✅ Achieves fastest runtime: 4.167 seconds
- ✅ Represents optimal balance of quality and performance

## Data Sources

- **Validation loss files:** `data/intermediates/densify_sz*/colmap_sfm_linearized/splats/val_20260621_*.jsonl`
- **Timing files:** `data/intermediates/densify_sz*/colmap_sfm_linearized/splats/running-time_20260621_*.jsonl`

## Sweep Command

```bash
uv run python pipeline.py \
    --config-path config --config-name hparam_sweep \
    --multirun \
    opensplat.densify_size_thresh=0.0025,0.005,0.01 \
    opensplat.densify_grad_thresh=0.0001,0.0002,0.0004
```

## Date

2026-06-21

#!/bin/bash
set -e

# Train OpenSplat on both SIFT_BRUTEFORCE and SIFT_LIGHTGLUE feature extraction methods
# This script compares the quality of different feature matching approaches

PROJECT_DIR="/Users/bc/brendanchambers/2026-06-18-iphone-video-to-splat"
OPENSPLAT_BIN="${PROJECT_DIR}/opensplat/build/opensplat"
NUM_ITERS=1500
TIMESTAMP=$(date +"%Y%m%d_%H%M")

# Configuration for both SIFT variants
SIFT_METHODS=("sift_bruteforce" "sift_lightglue")

echo "=========================================="
echo "OpenSplat SIFT Feature Comparison"
echo "Training: 1500 iterations per method"
echo "Timestamp: $TIMESTAMP"
echo "=========================================="

for METHOD in "${SIFT_METHODS[@]}"; do
    echo ""
    echo "─────────────────────────────────────────"
    METHOD_UPPER=$(echo $METHOD | tr 'a-z' 'A-Z')
    echo "Training: SIFT_${METHOD_UPPER}"
    echo "─────────────────────────────────────────"

    # Set paths based on method
    EXPERIMENT_NAME="test_4s_feature_comparison_max-num-features-8192_type-${METHOD}"
    DATA_DIR="${PROJECT_DIR}/data/intermediates/${EXPERIMENT_NAME}_distortion_corrected/sparse"
    IMAGES_DIR="${PROJECT_DIR}/data/intermediates/${EXPERIMENT_NAME}_distortion_corrected/images"
    OUTPUT_DIR="${PROJECT_DIR}/data/intermediates/${EXPERIMENT_NAME}_distortion_corrected/splats"
    OUTPUT_SUBDIR="${OUTPUT_DIR}/${NUM_ITERS}steps_${TIMESTAMP}"
    LOG_FILE="${PROJECT_DIR}/logs/opensplat_sift_${METHOD}_${TIMESTAMP}.log"

    # Create output directories
    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$OUTPUT_SUBDIR"
    mkdir -p "$(dirname "$LOG_FILE")"

    OUTPUT_FILENAME="model_${NUM_ITERS}steps.ply"
    OUTPUT_PATH="${OUTPUT_SUBDIR}/${OUTPUT_FILENAME}"

    echo "Input images: $IMAGES_DIR"
    echo "COLMAP data: $DATA_DIR"
    echo "Output: $OUTPUT_PATH"
    echo "Log file: $LOG_FILE"
    echo ""

    # Verify input paths exist
    if [ ! -d "$IMAGES_DIR" ]; then
        echo "ERROR: Images directory not found: $IMAGES_DIR"
        exit 1
    fi

    if [ ! -d "$DATA_DIR" ]; then
        echo "ERROR: COLMAP data directory not found: $DATA_DIR"
        exit 1
    fi

    # Run OpenSplat training
    echo "Starting training... (this may take a while)"
    $OPENSPLAT_BIN "$DATA_DIR" --colmap-image-path "$IMAGES_DIR" --output "$OUTPUT_PATH" --num-iters "$NUM_ITERS" | tee "$LOG_FILE"

    echo "✓ Training complete for $METHOD"
    echo "  Output: $OUTPUT_PATH"
    echo "  Log: $LOG_FILE"
done

echo ""
echo "=========================================="
echo "Training complete!"
echo "=========================================="
echo ""
echo "Models saved to:"
for METHOD in "${SIFT_METHODS[@]}"; do
    EXPERIMENT_NAME="test_4s_feature_comparison_max-num-features-8192_type-${METHOD}"
    OUTPUT_DIR="${PROJECT_DIR}/data/intermediates/${EXPERIMENT_NAME}_distortion_corrected/splats"
    OUTPUT_SUBDIR="${OUTPUT_DIR}/${NUM_ITERS}steps_${TIMESTAMP}"
    echo "  ${METHOD}: $OUTPUT_SUBDIR/"
done

echo ""
echo "To analyze and compare results:"
echo "  uv run python scripts/plot_training_metrics.py <log_file>"
echo "  Compare loss curves between both methods"

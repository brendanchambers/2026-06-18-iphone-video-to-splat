#!/bin/bash
set -e

# Load environment variables
source "$(dirname "$0")/.env"

# Accept semantic experiment name as argument
if [ -z "$1" ]; then
    echo "Usage: $0 <semantic_experiment_name>"
    echo "Example: $0 gardenbed_full_scene_max-num-features-256_type-sift_bruteforce"
    exit 1
fi

SEMANTIC_EXPERIMENT_NAME="$1"
EXPERIMENT_POSTFIX="_distortion_corrected"
FULL_EXPERIMENT_NAME="${SEMANTIC_EXPERIMENT_NAME}${EXPERIMENT_POSTFIX}"
TIMESTAMP=$(date +"%Y%m%d_%H%M")

# Path to compiled OpenSplat binary
OPENSPLAT_BIN="${PROJECT_DIR}/opensplat/build/opensplat"

# Define paths to COLMAP data and output folder
DATA_DIR="${PROJECT_DIR}/data/intermediates/${FULL_EXPERIMENT_NAME}/sparse"
IMAGES_DIR="${PROJECT_DIR}/data/intermediates/${FULL_EXPERIMENT_NAME}/images"
OUTPUT_DIR="${PROJECT_DIR}/data/intermediates/${FULL_EXPERIMENT_NAME}/splats"
OUTPUT_SUBDIR="${OUTPUT_DIR}/${NUM_ITERS}steps_${TIMESTAMP}"
LOG_FILE="${PROJECT_DIR}/logs/opensplat_${SEMANTIC_EXPERIMENT_NAME}.log"
TIMING_FILE="${PROJECT_DIR}/logs/opensplat_timings.jsonl"

# Validation paths
VAL_RENDER_FULL="${PROJECT_DIR}/${VAL_RENDER_DIR}"

echo "========================================================="
echo "Starting OpenSplat training on M4 Metal GPU..."
echo "Experiment: $SEMANTIC_EXPERIMENT_NAME"
echo "========================================================="

# Create output and logs directories if they don't exist
mkdir -p "$OUTPUT_DIR"
mkdir -p "$OUTPUT_SUBDIR"
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$VAL_RENDER_FULL"

# Generate semantic filename with iteration count, date, and time
OUTPUT_FILENAME="opensplat_output_numiters${NUM_ITERS}_${TIMESTAMP}.ply"
OUTPUT_PATH="${OUTPUT_SUBDIR}/${OUTPUT_FILENAME}"

# Record start time
START_TIME=$(date +%s%N)
START_TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

# Build validation parameters
VALIDATION_ARGS=""
if [ "$VAL_ENABLED" = "true" ]; then
    VALIDATION_ARGS="--val --val-image $VAL_IMAGE --val-render $VAL_RENDER_FULL --ssim-weight $SSIM_WEIGHT"
fi

echo "Logging to: $LOG_FILE"
echo "Output will be saved to: $OUTPUT_PATH"
echo "Validation enabled: $VAL_ENABLED (image: $VAL_IMAGE)"
echo "========================================================="

# Execute OpenSplat and log output
$OPENSPLAT_BIN "$DATA_DIR" --colmap-image-path "$IMAGES_DIR" --output "$OUTPUT_PATH" --num-iters "$NUM_ITERS" $VALIDATION_ARGS 2>&1 | tee "$LOG_FILE"

# Record end time and calculate elapsed time
END_TIME=$(date +%s%N)
END_TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
ELAPSED_NS=$((END_TIME - START_TIME))
ELAPSED_SECONDS=$(echo "scale=2; $ELAPSED_NS / 1000000000" | bc)

echo "========================================================="
echo "Training complete!"
echo "Output saved to: $OUTPUT_PATH"
echo "Elapsed time: ${ELAPSED_SECONDS}s"
echo "Training log saved to: $LOG_FILE"
echo "========================================================="

# Write timing results to JSONL file
{
    echo "{\"experiment\": \"$SEMANTIC_EXPERIMENT_NAME\", \"start_timestamp\": \"$START_TIMESTAMP\", \"end_timestamp\": \"$END_TIMESTAMP\", \"elapsed_seconds\": $ELAPSED_SECONDS, \"num_iters\": $NUM_ITERS, \"output_path\": \"$OUTPUT_PATH\", \"log_file\": \"$LOG_FILE\"}"
} >> "$TIMING_FILE"

echo "Timing results saved to: $TIMING_FILE"

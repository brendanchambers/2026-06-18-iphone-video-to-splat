#!/bin/bash
set -e

# Project root directory
PROJECT_ROOT="/Users/bc/brendanchambers/2026-06-18-iphone-video-to-splat"

# Experiment configuration
EXPERIMENT_NAME="current_scene"
EXPERIMENT_POSTFIX="_distortion_corrected"
FULL_EXPERIMENT_NAME="${EXPERIMENT_NAME}${EXPERIMENT_POSTFIX}"

# Path to compiled OpenSplat binary
OPENSPLAT_BIN="${PROJECT_ROOT}/opensplat/build/opensplat"

# Define paths to COLMAP data and output folder
DATA_DIR="${PROJECT_ROOT}/data/intermediates/${FULL_EXPERIMENT_NAME}/sparse"
IMAGES_DIR="${PROJECT_ROOT}/data/intermediates/${FULL_EXPERIMENT_NAME}/images"
OUTPUT_DIR="${PROJECT_ROOT}/data/intermediates/${FULL_EXPERIMENT_NAME}/opensplat_output"

echo "Starting OpenSplat training on M4 Metal GPU..."

# Execute OpenSplat (Adjust flags based on OpenSplat's CLI arguments)
$OPENSPLAT_BIN --input "$DATA_DIR" --colmap-image-path "$IMAGES_DIR" --output "$OUTPUT_DIR/scene.ply" -n 2000

echo "Training complete! Output saved to $OUTPUT_DIR/scene.ply"

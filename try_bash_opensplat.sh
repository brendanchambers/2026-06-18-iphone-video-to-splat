#!/bin/bash
set -e

# Path to your compiled OpenSplat binary
OPENSPLAT_BIN="/Users/bc/brendanchambers/2026-06-18-iphone-video-to-splat/opensplat/build/opensplat"

# Define paths to your COLMAP/nerfstudio data and output folder
DATA_DIR="/Users/bc/brendanchambers/2026-06-18-iphone-video-to-splat/data/intermediates/current_scene"
OUTPUT_DIR="/Users/bc/brendanchambers/2026-06-18-iphone-video-to-splat/data/intermediates/current_scene/opensplat_gs"

echo "Starting OpenSplat training on M4 Metal GPU..."

# Execute OpenSplat (Adjust flags based on OpenSplat's CLI arguments)
$OPENSPLAT_BIN --input "$DATA_DIR" --output "$OUTPUT_DIR/scene.ply"

echo "Training complete! Output saved to $OUTPUT_DIR/scene.ply"

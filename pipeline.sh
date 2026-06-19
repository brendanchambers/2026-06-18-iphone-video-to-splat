#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================================="
echo "Starting Full Pipeline: COLMAP + OpenSplat"
echo "========================================================="
echo ""

# Load environment variables from .env
source "$SCRIPT_DIR/.env"

# Stage 1: COLMAP SfM Processing
echo "STAGE 1: COLMAP Structure-from-Motion"
echo "========================================"
if bash "$SCRIPT_DIR/launch_colmap.sh"; then
    echo ""
    echo "✓ COLMAP stage completed successfully"
    echo ""
else
    echo ""
    echo "✗ COLMAP stage failed. Please check logs/colmap_pipeline.log"
    exit 1
fi

# Stage 2: OpenSplat Training
echo ""
echo "STAGE 2: OpenSplat Gaussian Splat Training"
echo "==========================================="
if bash "$SCRIPT_DIR/launch_opensplat.sh"; then
    echo ""
    echo "✓ OpenSplat stage completed successfully"
    echo ""
else
    echo ""
    echo "✗ OpenSplat stage failed. Please check logs/opensplat_pipeline.log"
    exit 1
fi

echo "========================================================="
echo "Full Pipeline Complete!"
echo "========================================================="
echo ""
echo "Results:"
echo "  - SfM reconstruction: data/intermediates/${EXPERIMENT_NAME}_distortion_corrected/"
echo "  - Gaussian Splat model: data/intermediates/${EXPERIMENT_NAME}_distortion_corrected/opensplat_output/scene.ply"
echo ""
echo "Logs:"
echo "  - COLMAP: logs/colmap_pipeline.log"
echo "  - OpenSplat: logs/opensplat_pipeline.log"
echo ""
echo "To visualize training loss:"
echo "  uv run python scripts/plot_training_loss.py"
echo "========================================================="

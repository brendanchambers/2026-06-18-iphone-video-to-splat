#!/bin/bash

#====================================================================
# Experiment Runner: Feature Matching Comparison
#====================================================================
#
# Orchestrates a full comparison experiment between feature matching
# strategies (exhaustive vs sequential) for 3D Gaussian Splatting.
#
# Runs:
# 1. COLMAP SfM with exhaustive and sequential matching
# 2. OpenSplat training on both outputs
# 3. Generates comparison report
#
# USAGE:
#   ./run_experiment.sh [options]
#
# OPTIONS:
#   --name <name>           Experiment name (required, e.g., gardenbed)
#   --video <path>          Video path (required, e.g., ./data/incoming/movies/video.mov)
#   --max-features <N>      Max SIFT features per image (default: 4096)
#   --iters <N>             OpenSplat training iterations (default: 500)
#   --matchers <list>       Matchers to compare (default: exhaustive,sequential)
#                           Options: exhaustive, sequential, or comma-separated list
#   --help                  Show this help message
#
# EXAMPLES:
#   ./run_experiment.sh --name test --video ./data/incoming/movies/video.mov
#   ./run_experiment.sh --name gardenbed --video ./data/incoming/movies/gardenbed.mov \
#       --max-features 8192 --iters 1500 --matchers exhaustive,sequential
#
#====================================================================

set -e

# Default values
EXPERIMENT_NAME=""
VIDEO_PATH=""
MAX_FEATURES=4096
NUM_ITERS=500
MATCHERS="exhaustive,sequential"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            EXPERIMENT_NAME="$2"
            shift 2
            ;;
        --video)
            VIDEO_PATH="$2"
            shift 2
            ;;
        --max-features)
            MAX_FEATURES="$2"
            shift 2
            ;;
        --iters)
            NUM_ITERS="$2"
            shift 2
            ;;
        --matchers)
            MATCHERS="$2"
            shift 2
            ;;
        --help)
            echo "Experiment Runner: Feature Matching Comparison"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --name <name>           Experiment name (required)"
            echo "  --video <path>          Video path (required)"
            echo "  --max-features <N>      Max SIFT features (default: 4096)"
            echo "  --iters <N>             Training iterations (default: 500)"
            echo "  --matchers <list>       Matchers to test (default: exhaustive,sequential)"
            echo "  --help                  Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --name test --video ./data/incoming/movies/video.mov"
            echo "  $0 --name gardenbed --video ./data/incoming/movies/gardenbed.mov \\"
            echo "      --max-features 8192 --iters 1500"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$EXPERIMENT_NAME" ]; then
    echo "Error: --name is required"
    echo "Use --help for usage information"
    exit 1
fi

if [ -z "$VIDEO_PATH" ]; then
    echo "Error: --video is required"
    echo "Use --help for usage information"
    exit 1
fi

# Convert matcher list to array
IFS=',' read -ra MATCHER_ARRAY <<< "$MATCHERS"

echo "=========================================================="
echo "Starting Experiment: Feature Matching Comparison"
echo "=========================================================="
echo "Experiment Name:    $EXPERIMENT_NAME"
echo "Video Path:         $VIDEO_PATH"
echo "Max SIFT Features:  $MAX_FEATURES"
echo "Training Iters:     $NUM_ITERS"
echo "Matchers:           ${MATCHER_ARRAY[*]}"
echo "=========================================================="
echo ""

# Create log directory
mkdir -p "$PROJECT_DIR/logs"
EXPERIMENT_DIR="$PROJECT_DIR/data/intermediates"
REPORT_FILE="$PROJECT_DIR/${EXPERIMENT_NAME}_comparison_report.md"

# Initialize report
cat > "$REPORT_FILE" << EOF
# Feature Matching Comparison Experiment
## $EXPERIMENT_NAME

**Date**: $(date "+%Y-%m-%d %H:%M:%S")
**Video**: $VIDEO_PATH
**Config**: Max SIFT Features = $MAX_FEATURES, Training Iterations = $NUM_ITERS

---

## Execution Summary

EOF

echo "Step 1/3: Running COLMAP SfM pipelines..."
echo "" >> "$REPORT_FILE"
echo "## 1. COLMAP SfM Results" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Run COLMAP for each matcher
# Store results in files instead of associative arrays (bash 3.2 compatible)
COLMAP_TIMES_FILE=$(mktemp)
for matcher in "${MATCHER_ARRAY[@]}"; do
    echo ""
    echo "Running COLMAP with $matcher matching..."
    COLMAP_LOG="$PROJECT_DIR/logs/colmap_${EXPERIMENT_NAME}_${matcher}.log"

    # Run COLMAP
    chmod +x "$PROJECT_DIR/launch_colmap.sh"
    "$PROJECT_DIR/launch_colmap.sh" \
        --matcher "$matcher" \
        --max-num-features "$MAX_FEATURES" \
        --experiment "$EXPERIMENT_NAME" \
        --video "$VIDEO_PATH" 2>&1 | tee "$COLMAP_LOG"

    # Extract timing
    ELAPSED=$(grep "Elapsed time:" "$COLMAP_LOG" | tail -1 | awk '{print $3}')
    echo "$matcher:$ELAPSED" >> "$COLMAP_TIMES_FILE"

    echo "### $matcher Matching" >> "$REPORT_FILE"
    echo "- **Time**: $ELAPSED" >> "$REPORT_FILE"
    echo "- **Output**: \`${EXPERIMENT_NAME}_${matcher}_max-num-features-${MAX_FEATURES}_distortion_corrected/\`" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
done

echo ""
echo "Step 2/3: Running OpenSplat training..."
echo "" >> "$REPORT_FILE"
echo "## 2. OpenSplat Training Results" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Create a temporary .env with overrides for OpenSplat runs
TMP_ENV=$(mktemp)
cp "$PROJECT_DIR/.env" "$TMP_ENV"

# Run OpenSplat for each matcher
# Store results in files instead of associative arrays (bash 3.2 compatible)
OPENSPLAT_LOSSES_FILE=$(mktemp)
for matcher in "${MATCHER_ARRAY[@]}"; do
    echo ""
    echo "Training OpenSplat with $matcher COLMAP data..."

    # Update .env temporarily
    sed -i '' "s/^EXPERIMENT_NAME=.*/EXPERIMENT_NAME=\"${EXPERIMENT_NAME}_${matcher}\"/" "$TMP_ENV"
    sed -i '' "s/^NUM_ITERS=.*/NUM_ITERS=$NUM_ITERS/" "$TMP_ENV"

    # Run with temporary .env
    OPENSPLAT_LOG="$PROJECT_DIR/logs/opensplat_${EXPERIMENT_NAME}_${matcher}.log"

    # Create temporary launch script that sources our .env
    (
        source "$TMP_ENV"
        cd "$PROJECT_DIR"
        chmod +x "$PROJECT_DIR/launch_opensplat.sh"
        "$PROJECT_DIR/launch_opensplat.sh" 2>&1 | tee "$OPENSPLAT_LOG"
    )

    # Extract validation loss
    VAL_LOSS=$(grep "validation loss:" "$OPENSPLAT_LOG" | tail -1 | awk '{print $(NF-1)}')
    echo "$matcher:$VAL_LOSS" >> "$OPENSPLAT_LOSSES_FILE"

    echo "### $matcher - OpenSplat" >> "$REPORT_FILE"
    echo "- **Training Iterations**: $NUM_ITERS" >> "$REPORT_FILE"
    echo "- **Final Validation Loss**: $VAL_LOSS" >> "$REPORT_FILE"
    echo "- **Log**: \`logs/opensplat_${EXPERIMENT_NAME}_${matcher}.log\`" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
done

# Restore original .env
mv "$TMP_ENV" "$PROJECT_DIR/.env"

echo ""
echo "Step 3/3: Generating comparison report..."
echo "" >> "$REPORT_FILE"
echo "## 3. Comparison Summary" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "| Matcher | COLMAP Time | Validation Loss |" >> "$REPORT_FILE"
echo "|---------|-------------|-----------------|" >> "$REPORT_FILE"

for matcher in "${MATCHER_ARRAY[@]}"; do
    TIME=$(grep "^${matcher}:" "$COLMAP_TIMES_FILE" | cut -d: -f2 | head -1)
    LOSS=$(grep "^${matcher}:" "$OPENSPLAT_LOSSES_FILE" | cut -d: -f2 | head -1)
    TIME=${TIME:-"N/A"}
    LOSS=${LOSS:-"N/A"}
    echo "| $matcher | $TIME | $LOSS |" >> "$REPORT_FILE"
done

echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "Report generated: $(date "+%Y-%m-%d %H:%M:%S")" >> "$REPORT_FILE"

echo ""
echo "=========================================================="
echo "Experiment Complete!"
echo "=========================================================="
echo "Report saved to: $REPORT_FILE"
echo ""
echo "Results:"
for matcher in "${MATCHER_ARRAY[@]}"; do
    TIME=$(grep "^${matcher}:" "$COLMAP_TIMES_FILE" | cut -d: -f2 | head -1)
    LOSS=$(grep "^${matcher}:" "$OPENSPLAT_LOSSES_FILE" | cut -d: -f2 | head -1)
    echo "  $matcher:"
    echo "    COLMAP Time: ${TIME:-N/A}"
    echo "    Validation Loss: ${LOSS:-N/A}"
done
echo ""
echo "=========================================================="

# Cleanup temporary files
rm -f "$COLMAP_TIMES_FILE" "$OPENSPLAT_LOSSES_FILE"

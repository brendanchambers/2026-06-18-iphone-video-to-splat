#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Load environment variables
source "$(dirname "$0")/.env"

#====================================================================
# Loop Detection Comparison Experiment
#====================================================================
#
# Compares sequential frame matching with and without vocabulary tree
# loop detection. Runs both COLMAP pipelines with timing, then trains
# OpenSplat models for quality comparison.
#
# USAGE:
#   ./run_loop_detection_experiment.sh [options]
#
# OPTIONS:
#   --name <name>           Experiment name (default: loop_detection_test)
#   --video <path>          Video path (overrides .env)
#   --max-features <N>      Max SIFT features (default: 4096)
#   --iters <N>             Training iterations (default: 1000)
#   --help                  Show this help message
#
# EXAMPLES:
#   ./run_loop_detection_experiment.sh --name myexp --video video.mov
#   ./run_loop_detection_experiment.sh --name myexp --max-features 8192 --iters 1500
#
#====================================================================

# Default values
EXPERIMENT_NAME="loop_detection_test"
VIDEO_PATH="${VIDEO_PATH:-./data/incoming/movies/gardenbed_2026-06-17.mov}"
MAX_NUM_FEATURES=4096
NUM_ITERS=1000
PROJECT_DIR="${PROJECT_DIR:-.}"

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
            MAX_NUM_FEATURES="$2"
            shift 2
            ;;
        --iters)
            NUM_ITERS="$2"
            shift 2
            ;;
        --help)
            echo "Loop Detection Comparison Experiment"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --name <name>           Experiment name (default: loop_detection_test)"
            echo "  --video <path>          Video path"
            echo "  --max-features <N>      Max SIFT features (default: 4096)"
            echo "  --iters <N>             Training iterations (default: 1000)"
            echo "  --help                  Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --name myexp --video video.mov"
            echo "  $0 --name myexp --max-features 8192 --iters 1500"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Ensure output directories exist
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/data/intermediates"

# Create report file path
REPORT_FILE="$PROJECT_DIR/${EXPERIMENT_NAME}_loop_detection_report.md"

echo "========================================================="
echo "Starting Loop Detection Comparison Experiment"
echo "========================================================="
echo "Experiment Name:      $EXPERIMENT_NAME"
echo "Video Path:           $VIDEO_PATH"
echo "Max SIFT Features:    $MAX_NUM_FEATURES"
echo "Training Iterations:  $NUM_ITERS"
echo "Report Path:          $REPORT_FILE"
echo "========================================================="

# Initialize report
cat > "$REPORT_FILE" << 'EOF'
# Loop Detection Comparison Report

This report compares sequential frame matching with and without vocabulary tree-based loop detection.

## Experiment Parameters

EOF

echo "Experiment Name: $EXPERIMENT_NAME" >> "$REPORT_FILE"
echo "Video: $VIDEO_PATH" >> "$REPORT_FILE"
echo "Max Features: $MAX_NUM_FEATURES" >> "$REPORT_FILE"
echo "Training Iterations: $NUM_ITERS" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Stage 1: Run COLMAP without loop detection
echo ""
echo "========================================================="
echo "STAGE 1: Sequential Matching WITHOUT Loop Detection"
echo "========================================================="
COLMAP_START=$(date +%s)

./launch_colmap.sh \
    --matcher sequential \
    --max-num-features "$MAX_NUM_FEATURES" \
    --experiment "${EXPERIMENT_NAME}_no_loop" \
    --video "$VIDEO_PATH" | tee -a "$PROJECT_DIR/logs/loop_detection_${EXPERIMENT_NAME}_stage1.log"

COLMAP_END=$(date +%s)
COLMAP_TIME_NO_LOOP=$((COLMAP_END - COLMAP_START))

echo "Stage 1 complete. Elapsed time: ${COLMAP_TIME_NO_LOOP}s"
echo "" >> "$REPORT_FILE"
echo "## Stage 1: Sequential Matching WITHOUT Loop Detection" >> "$REPORT_FILE"
echo "COLMAP Time: ${COLMAP_TIME_NO_LOOP}s" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Stage 2: Run COLMAP with loop detection
echo ""
echo "========================================================="
echo "STAGE 2: Sequential Matching WITH Loop Detection"
echo "========================================================="
COLMAP_START=$(date +%s)

./launch_colmap.sh \
    --matcher sequential \
    --loop-detection \
    --max-num-features "$MAX_NUM_FEATURES" \
    --experiment "${EXPERIMENT_NAME}_with_loop" \
    --video "$VIDEO_PATH" | tee -a "$PROJECT_DIR/logs/loop_detection_${EXPERIMENT_NAME}_stage2.log"

COLMAP_END=$(date +%s)
COLMAP_TIME_WITH_LOOP=$((COLMAP_END - COLMAP_START))

echo "Stage 2 complete. Elapsed time: ${COLMAP_TIME_WITH_LOOP}s"
echo "" >> "$REPORT_FILE"
echo "## Stage 2: Sequential Matching WITH Loop Detection" >> "$REPORT_FILE"
echo "COLMAP Time: ${COLMAP_TIME_WITH_LOOP}s" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Calculate COLMAP time difference
COLMAP_DIFF=$((COLMAP_TIME_WITH_LOOP - COLMAP_TIME_NO_LOOP))
COLMAP_PERCENT=$(echo "scale=1; ($COLMAP_DIFF / $COLMAP_TIME_NO_LOOP) * 100" | bc)

echo "" >> "$REPORT_FILE"
echo "## COLMAP Timing Comparison" >> "$REPORT_FILE"
echo "- Without loop detection: ${COLMAP_TIME_NO_LOOP}s" >> "$REPORT_FILE"
echo "- With loop detection:    ${COLMAP_TIME_WITH_LOOP}s" >> "$REPORT_FILE"
echo "- Difference: ${COLMAP_DIFF}s (${COLMAP_PERCENT}%)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Stage 3: Train OpenSplat models for both variants
echo ""
echo "========================================================="
echo "STAGE 3: OpenSplat Training (WITHOUT Loop Detection)"
echo "========================================================="
OPENSPLAT_START=$(date +%s)

# Temporarily update .env for this run
ORIGINAL_EXPERIMENT_NAME="$EXPERIMENT_NAME"
export EXPERIMENT_NAME="${EXPERIMENT_NAME}_no_loop"

./launch_opensplat.sh | tee -a "$PROJECT_DIR/logs/loop_detection_${ORIGINAL_EXPERIMENT_NAME}_stage3a.log"

OPENSPLAT_END=$(date +%s)
OPENSPLAT_TIME_NO_LOOP=$((OPENSPLAT_END - OPENSPLAT_START))

echo "Stage 3a complete. OpenSplat time: ${OPENSPLAT_TIME_NO_LOOP}s"
echo "" >> "$REPORT_FILE"
echo "## Stage 3: OpenSplat Training (WITHOUT Loop Detection)" >> "$REPORT_FILE"
echo "Training Time: ${OPENSPLAT_TIME_NO_LOOP}s" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo ""
echo "========================================================="
echo "STAGE 4: OpenSplat Training (WITH Loop Detection)"
echo "========================================================="
OPENSPLAT_START=$(date +%s)

export EXPERIMENT_NAME="${ORIGINAL_EXPERIMENT_NAME}_with_loop"

./launch_opensplat.sh | tee -a "$PROJECT_DIR/logs/loop_detection_${ORIGINAL_EXPERIMENT_NAME}_stage3b.log"

OPENSPLAT_END=$(date +%s)
OPENSPLAT_TIME_WITH_LOOP=$((OPENSPLAT_END - OPENSPLAT_START))

echo "Stage 4 complete. OpenSplat time: ${OPENSPLAT_TIME_WITH_LOOP}s"
echo "" >> "$REPORT_FILE"
echo "## Stage 4: OpenSplat Training (WITH Loop Detection)" >> "$REPORT_FILE"
echo "Training Time: ${OPENSPLAT_TIME_WITH_LOOP}s" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Restore experiment name
export EXPERIMENT_NAME="$ORIGINAL_EXPERIMENT_NAME"

# Calculate OpenSplat time difference
OPENSPLAT_DIFF=$((OPENSPLAT_TIME_WITH_LOOP - OPENSPLAT_TIME_NO_LOOP))
OPENSPLAT_PERCENT=$(echo "scale=1; ($OPENSPLAT_DIFF / $OPENSPLAT_TIME_NO_LOOP) * 100" | bc)

echo "" >> "$REPORT_FILE"
echo "## OpenSplat Timing Comparison" >> "$REPORT_FILE"
echo "- Without loop detection: ${OPENSPLAT_TIME_NO_LOOP}s" >> "$REPORT_FILE"
echo "- With loop detection:    ${OPENSPLAT_TIME_WITH_LOOP}s" >> "$REPORT_FILE"
echo "- Difference: ${OPENSPLAT_DIFF}s (${OPENSPLAT_PERCENT}%)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Overall timing summary
TOTAL_NO_LOOP=$((COLMAP_TIME_NO_LOOP + OPENSPLAT_TIME_NO_LOOP))
TOTAL_WITH_LOOP=$((COLMAP_TIME_WITH_LOOP + OPENSPLAT_TIME_WITH_LOOP))
TOTAL_DIFF=$((TOTAL_WITH_LOOP - TOTAL_NO_LOOP))
TOTAL_PERCENT=$(echo "scale=1; ($TOTAL_DIFF / $TOTAL_NO_LOOP) * 100" | bc)

echo "" >> "$REPORT_FILE"
echo "## Total Pipeline Timing" >> "$REPORT_FILE"
echo "- Without loop detection: ${TOTAL_NO_LOOP}s" >> "$REPORT_FILE"
echo "- With loop detection:    ${TOTAL_WITH_LOOP}s" >> "$REPORT_FILE"
echo "- Difference: ${TOTAL_DIFF}s (${TOTAL_PERCENT}%)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"
echo "## Results" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "Generated models:" >> "$REPORT_FILE"
ls -lh "$PROJECT_DIR/data/intermediates/${EXPERIMENT_NAME}_no_loop_distortion_corrected/splats/"*/*.ply 2>/dev/null | awk '{print "- " $NF}' >> "$REPORT_FILE" || echo "- (No models found yet)" >> "$REPORT_FILE"
ls -lh "$PROJECT_DIR/data/intermediates/${EXPERIMENT_NAME}_with_loop_distortion_corrected/splats/"*/*.ply 2>/dev/null | awk '{print "- " $NF}' >> "$REPORT_FILE" || echo "- (No models found yet)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"
echo "## Conclusion" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "Loop detection impact:" >> "$REPORT_FILE"
if [ "$COLMAP_DIFF" -gt 0 ]; then
    echo "- COLMAP matching was **${COLMAP_PERCENT}% slower** with loop detection" >> "$REPORT_FILE"
else
    echo "- COLMAP matching was **${COLMAP_PERCENT}% faster** with loop detection" >> "$REPORT_FILE"
fi

if [ "$OPENSPLAT_DIFF" -gt 0 ]; then
    echo "- OpenSplat training was **${OPENSPLAT_PERCENT}% slower** with loop detection results" >> "$REPORT_FILE"
else
    echo "- OpenSplat training was **${OPENSPLAT_PERCENT}% faster** with loop detection results" >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"
echo "**Report generated:** $(date)" >> "$REPORT_FILE"

echo ""
echo "========================================================="
echo "Loop Detection Experiment Complete!"
echo "========================================================="
echo ""
echo "Summary:"
echo "  COLMAP without loop:  ${COLMAP_TIME_NO_LOOP}s"
echo "  COLMAP with loop:     ${COLMAP_TIME_WITH_LOOP}s (${COLMAP_PERCENT}%)"
echo "  OpenSplat without:    ${OPENSPLAT_TIME_NO_LOOP}s"
echo "  OpenSplat with:       ${OPENSPLAT_TIME_WITH_LOOP}s (${OPENSPLAT_PERCENT}%)"
echo "  Total without:        ${TOTAL_NO_LOOP}s"
echo "  Total with:           ${TOTAL_WITH_LOOP}s (${TOTAL_PERCENT}%)"
echo ""
echo "Full report: $REPORT_FILE"
echo "========================================================="

#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Load environment variables
source "$(dirname "$0")/.env"

#====================================================================
# COLMAP Photogrammetry Pipeline (Unified)
#====================================================================
#
# Runs the full COLMAP SfM pipeline with configurable feature matching:
#
# 1. Frame Extraction - Extracts frames from video at 2 fps
# 2. Feature Extraction - Detects SIFT features in each image
# 3. Feature Matching - Matches features (exhaustive or sequential)
# 4. Sparse Reconstruction - Computes camera poses & 3D point cloud
# 5. Distortion Correction - Undistorts images for use with OpenSplat
#
# USAGE:
#   ./launch_colmap.sh [options]
#
# OPTIONS:
#   --matcher <type>        Feature matching type: exhaustive or sequential (default: exhaustive)
#   --max-num-features <N>  Max SIFT features per image (overrides .env MAX_NUM_FEATURES)
#   --experiment <name>     Experiment name (overrides .env EXPERIMENT_NAME)
#   --video <path>          Video path (overrides .env VIDEO_PATH)
#   --loop-detection        Enable vocabulary tree loop detection (sequential only)
#   --vocab-tree <path>     Path to vocabulary tree file (default: data/incoming/vocabulary_trees/vocab_tree_flickr100K_words32K.bin)
#   --help                  Show this help message
#
# EXAMPLES:
#   ./launch_colmap.sh --matcher exhaustive --max-num-features 8192
#   ./launch_colmap.sh --matcher sequential --max-num-features 4096
#   ./launch_colmap.sh --matcher sequential --loop-detection --max-num-features 4096
#
#====================================================================

# Default values from .env
MATCHER=${MATCHER:-exhaustive}
MAX_NUM_FEATURES=${MAX_NUM_FEATURES:-8192}
EXPERIMENT_NAME=${EXPERIMENT_NAME:-gardenbed}
VIDEO_PATH=${VIDEO_PATH:-./data/incoming/movies/gardenbed_2026-06-17.mov}
LOOP_DETECTION=0
VOCAB_TREE_PATH="${PROJECT_DIR}/data/incoming/vocabulary_trees/vocab_tree_flickr100K_words32K.bin"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --matcher)
            MATCHER="$2"
            shift 2
            ;;
        --max-num-features)
            MAX_NUM_FEATURES="$2"
            shift 2
            ;;
        --experiment)
            EXPERIMENT_NAME="$2"
            shift 2
            ;;
        --video)
            VIDEO_PATH="$2"
            shift 2
            ;;
        --loop-detection)
            LOOP_DETECTION=1
            shift 1
            ;;
        --vocab-tree)
            VOCAB_TREE_PATH="$2"
            shift 2
            ;;
        --help)
            echo "COLMAP Photogrammetry Pipeline (Unified)"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --matcher <type>        Feature matching: exhaustive or sequential (default: exhaustive)"
            echo "  --max-num-features <N>  Max SIFT features per image (default: 8192)"
            echo "  --experiment <name>     Experiment name (default: gardenbed)"
            echo "  --video <path>          Video path (default: from .env)"
            echo "  --loop-detection        Enable vocabulary tree loop detection (sequential only)"
            echo "  --vocab-tree <path>     Path to vocabulary tree file"
            echo "  --help                  Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --matcher exhaustive --max-num-features 8192"
            echo "  $0 --matcher sequential --max-num-features 4096"
            echo "  $0 --matcher sequential --loop-detection --max-num-features 4096"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate matcher type
if [ "$MATCHER" != "exhaustive" ] && [ "$MATCHER" != "sequential" ]; then
    echo "Error: --matcher must be 'exhaustive' or 'sequential', got '$MATCHER'"
    exit 1
fi

# Warn if loop detection is requested with exhaustive matching
if [ "$LOOP_DETECTION" = "1" ] && [ "$MATCHER" != "sequential" ]; then
    echo "Warning: Loop detection only works with sequential matching. Ignoring --loop-detection flag."
    LOOP_DETECTION=0
fi

# Validate vocabulary tree exists if loop detection enabled
if [ "$LOOP_DETECTION" = "1" ] && [ ! -f "$VOCAB_TREE_PATH" ]; then
    echo "Error: Vocabulary tree not found at $VOCAB_TREE_PATH"
    exit 1
fi

if [ -z "$VIDEO_PATH" ] || [ -z "$PROJECT_DIR" ]; then
    echo "Error: VIDEO_PATH and PROJECT_DIR must be set in .env"
    exit 1
fi

# Feature extraction configuration (hardcoded to SIFT)
FEATURE_BASE="SIFT"
FEATURE_MATCHING="SIFT_BRUTEFORCE"

# Generate semantic output directory name
# Format: experiment_name_matcher_max-num-features-8192[_loop]
PARAM_SUFFIX="${MATCHER}_max-num-features-${MAX_NUM_FEATURES}"
if [ "$LOOP_DETECTION" = "1" ]; then
    PARAM_SUFFIX="${PARAM_SUFFIX}_loop"
fi
SEMANTIC_EXPERIMENT_NAME="${EXPERIMENT_NAME}_${PARAM_SUFFIX}"

# Create directory structure expected by OpenSplat
IMAGES_DIR="$PROJECT_DIR/data/intermediates/$SEMANTIC_EXPERIMENT_NAME/images"
SPARSE_DIR="$PROJECT_DIR/data/intermediates/$SEMANTIC_EXPERIMENT_NAME/sparse"
DATABASE_PATH="$PROJECT_DIR/data/intermediates/$SEMANTIC_EXPERIMENT_NAME/database.db"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/colmap_${SEMANTIC_EXPERIMENT_NAME}.log"
TIMING_FILE="$LOG_DIR/colmap_timings.jsonl"

mkdir -p "$IMAGES_DIR"
mkdir -p "$SPARSE_DIR"
mkdir -p "$LOG_DIR"

# Record start time
START_TIME=$(date +%s%N)
START_TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

echo "========================================================="
echo "Starting COLMAP Pipeline (Matcher: $MATCHER)"
if [ "$LOOP_DETECTION" = "1" ]; then
    echo "Loop Detection: ENABLED (vocabulary tree: $(basename "$VOCAB_TREE_PATH"))"
else
    echo "Loop Detection: DISABLED"
fi
echo "Input video: $VIDEO_PATH"
echo "Experiment: $SEMANTIC_EXPERIMENT_NAME"
echo "Max SIFT features: $MAX_NUM_FEATURES"
echo "Output logged to: $LOG_FILE"
echo "=========================================================" | tee "$LOG_FILE"

# --- Step 1: Extract Frames from Video ---
# Extracting 2 to 3 frames per second is usually ideal for tracking.
# Adjust 'fps=2' higher if your video camera moves very fast.
echo "--> Step 1: Extracting frames using ffmpeg..." | tee -a "$LOG_FILE"
ffmpeg -i "$VIDEO_PATH" -vf "fps=2" -q:v 2 "$IMAGES_DIR/frame_%04d.jpg" 2>&1 | tee -a "$LOG_FILE"

# --- Step 2: Feature Extraction ---
# Detects SIFT features across all extracted frames
echo "--> Step 2: Extracting SIFT features (max_num_features=$MAX_NUM_FEATURES)..." | tee -a "$LOG_FILE"
colmap feature_extractor \
    --database_path "$DATABASE_PATH" \
    --image_path "$IMAGES_DIR" \
    --ImageReader.camera_model "RADIAL" \
    --ImageReader.single_camera 1 \
    --ImageReader.default_focal_length_factor 1.2 \
    --FeatureExtraction.type "$FEATURE_BASE" \
    --FeatureExtraction.use_gpu 1 \
    --FeatureExtraction.gpu_index -1 \
    --SiftExtraction.max_num_features "$MAX_NUM_FEATURES" \
    --SiftExtraction.first_octave -1 \
    --SiftExtraction.num_octaves 4 \
    --SiftExtraction.octave_resolution 3 \
    --SiftExtraction.peak_threshold 0.00667 \
    --SiftExtraction.edge_threshold 10 \
    --SiftExtraction.estimate_affine_shape 0 \
    --SiftExtraction.max_num_orientations 2 \
    --SiftExtraction.upright 0 2>&1 | tee -a "$LOG_FILE"

# --- Step 3: Feature Matching ---
# Links corresponding SIFT features across image pairs
echo "--> Step 3: Matching SIFT features ($MATCHER)..." | tee -a "$LOG_FILE"

if [ "$MATCHER" = "exhaustive" ]; then
    echo "Using exhaustive brute force matching..." | tee -a "$LOG_FILE"
    colmap exhaustive_matcher \
        --database_path "$DATABASE_PATH" \
        --FeatureMatching.type "$FEATURE_MATCHING" \
        --FeatureMatching.use_gpu 1 \
        --FeatureMatching.gpu_index -1 \
        --FeatureMatching.guided_matching 0 \
        --FeatureMatching.skip_geometric_verification 0 \
        --FeatureMatching.max_num_matches 32768 \
        --SiftMatching.max_ratio 0.8 \
        --SiftMatching.max_distance 0.7 \
        --SiftMatching.cross_check 1 \
        --SiftMatching.cpu_brute_force_matcher 0 \
        --TwoViewGeometry.min_num_inliers 15 \
        --TwoViewGeometry.max_error 4 \
        --TwoViewGeometry.confidence 0.999 \
        --TwoViewGeometry.max_num_trials 10000 \
        --TwoViewGeometry.min_inlier_ratio 0.25 \
        --ExhaustiveMatching.block_size 50 2>&1 | tee -a "$LOG_FILE"
else
    echo "Using sequential matching..." | tee -a "$LOG_FILE"

    # Build loop detection parameters if enabled
    LOOP_DETECTION_ARGS=""
    if [ "$LOOP_DETECTION" = "1" ]; then
        echo "Enabling vocabulary tree loop detection..." | tee -a "$LOG_FILE"
        LOOP_DETECTION_ARGS="--SequentialMatching.loop_detection 1 \
        --SequentialMatching.loop_detection_period 10 \
        --SequentialMatching.loop_detection_num_images 50 \
        --SequentialMatching.loop_detection_num_nearest_neighbors 1 \
        --SequentialMatching.loop_detection_num_checks 64 \
        --SequentialMatching.vocab_tree_path $VOCAB_TREE_PATH"
    fi

    colmap sequential_matcher \
        --database_path "$DATABASE_PATH" \
        --FeatureMatching.type "$FEATURE_MATCHING" \
        --FeatureMatching.use_gpu 1 \
        --FeatureMatching.gpu_index -1 \
        --FeatureMatching.guided_matching 0 \
        --FeatureMatching.skip_geometric_verification 0 \
        --FeatureMatching.max_num_matches 32768 \
        --SiftMatching.max_ratio 0.8 \
        --SiftMatching.max_distance 0.7 \
        --SiftMatching.cross_check 1 \
        --SiftMatching.cpu_brute_force_matcher 0 \
        --TwoViewGeometry.min_num_inliers 15 \
        --TwoViewGeometry.max_error 4 \
        --TwoViewGeometry.confidence 0.999 \
        --TwoViewGeometry.max_num_trials 10000 \
        --TwoViewGeometry.min_inlier_ratio 0.25 \
        --SequentialMatching.overlap 5 \
        --SequentialMatching.quadratic_overlap 1 \
        $LOOP_DETECTION_ARGS 2>&1 | tee -a "$LOG_FILE"
fi

# --- Step 4: Sparse Reconstruction ---
# Calculates camera locations and the 3D sparse point cloud
echo "--> Step 4: Generating 3D sparse reconstruction..." | tee -a "$LOG_FILE"
colmap mapper \
    --database_path "$DATABASE_PATH" \
    --image_path "$IMAGES_DIR" \
    --output_path "$SPARSE_DIR" \
    --Mapper.multiple_models 1 \
    --Mapper.max_num_models 50 \
    --Mapper.min_model_size 10 \
    --Mapper.init_num_trials 200 \
    --Mapper.extract_colors 1 \
    --Mapper.num_threads -1 \
    --Mapper.min_focal_length_ratio 0.1 \
    --Mapper.max_focal_length_ratio 10 \
    --Mapper.ba_refine_focal_length 1 \
    --Mapper.ba_refine_principal_point 0 \
    --Mapper.ba_refine_extra_params 1 \
    --Mapper.ba_local_max_num_iterations 25 \
    --Mapper.ba_global_max_num_iterations 50 \
    --Mapper.ba_global_frames_freq 500 \
    --Mapper.ba_global_points_freq 250000 \
    --Mapper.filter_max_reproj_error 4 \
    --Mapper.filter_min_tri_angle 1.5 \
    --Mapper.init_max_error 4 \
    --Mapper.init_min_tri_angle 16 \
    --Mapper.abs_pose_max_error 12 \
    --Mapper.abs_pose_min_num_inliers 30 2>&1 | tee -a "$LOG_FILE"

# --- Step 5: Distortion Correction ---
# Generates undistorted images and corrected camera poses for OpenSplat
echo "--> Step 5: Correcting camera distortion..." | tee -a "$LOG_FILE"
DISTORTION_CORRECTED_DIR="${PROJECT_DIR}/data/intermediates/${SEMANTIC_EXPERIMENT_NAME}_distortion_corrected"
colmap image_undistorter \
    --image_path "$IMAGES_DIR" \
    --input_path "$SPARSE_DIR/0" \
    --output_path "$DISTORTION_CORRECTED_DIR" \
    --output_type "COLMAP" \
    --copy_policy "copy" \
    --blank_pixels 0 \
    --min_scale 0.2 \
    --max_scale 2 \
    --max_image_size -1 \
    --num_patch_match_src_images 20 \
    --jpeg_quality -1 2>&1 | tee -a "$LOG_FILE"

# Record end time and calculate elapsed time
END_TIME=$(date +%s%N)
END_TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
ELAPSED_NS=$((END_TIME - START_TIME))
ELAPSED_SECONDS=$(echo "scale=2; $ELAPSED_NS / 1000000000" | bc)

echo "=========================================================" | tee -a "$LOG_FILE"
echo "COLMAP Pipeline complete!" | tee -a "$LOG_FILE"
echo "Your OpenSplat-ready dataset is located at:" | tee -a "$LOG_FILE"
echo "  $DISTORTION_CORRECTED_DIR" | tee -a "$LOG_FILE"
echo "Elapsed time: ${ELAPSED_SECONDS}s" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "=========================================================" | tee -a "$LOG_FILE"

# Write timing results to JSONL file
{
    echo "{\"experiment\": \"$SEMANTIC_EXPERIMENT_NAME\", \"start_timestamp\": \"$START_TIMESTAMP\", \"end_timestamp\": \"$END_TIMESTAMP\", \"elapsed_seconds\": $ELAPSED_SECONDS, \"max_num_features\": $MAX_NUM_FEATURES, \"matcher\": \"$MATCHER\", \"loop_detection\": $LOOP_DETECTION, \"video_input\": \"$VIDEO_PATH\", \"log_file\": \"$LOG_FILE\"}"
} >> "$TIMING_FILE"

echo "Timing results saved to: $TIMING_FILE"

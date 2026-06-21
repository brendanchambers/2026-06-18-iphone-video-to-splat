#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Load environment variables
source "$(dirname "$0")/.env"

#====================================================================
# COLMAP Pipeline with Explicit Parameter Documentation
#====================================================================
#
# This script runs the full COLMAP photogrammetry pipeline:
# 1. Frame Extraction - Extracts frames from video at specified fps
# 2. Feature Extraction - Detects SIFT features in each image
# 3. Feature Matching - Matches features between image pairs
# 4. Sparse Reconstruction - Computes camera poses & 3D point cloud
# 5. Distortion Correction - Undistorts images for use with OpenSplat
#
# Output is logged to logs/colmap_pipeline.log
#
# All parameters below are set to COLMAP defaults. Customize as needed:
#
# COMMON TWEAKS:
# - Feature quality: Adjust SiftExtraction.max_num_features (default: 8192)
#   Higher = more features detected, slower. Try 4096-16384.
# - Feature matching: Adjust SiftMatching.max_ratio (default: 0.8)
#   Lower = stricter matching, fewer false matches.
# - Reconstruction quality: Adjust Mapper.filter_max_reproj_error (default: 4)
#   Lower = stricter filtering, potentially fewer 3D points.
# - Memory usage: Adjust SequentialMatching.overlap (default: 20)
#   Lower = fewer comparisons, faster. Higher = more thorough but slower.
#
#====================================================================


if [ -z "$VIDEO_PATH" ] || [ -z "$PROJECT_DIR" ]; then
    echo "Usage: $0 <path_to_video.mov> <path_to_output_project_dir>"
    exit 1
fi

# Create directory structure expected by OpenSplat
IMAGES_DIR="$PROJECT_DIR/data/intermediates/$EXPERIMENT_NAME/images"
SPARSE_DIR="$PROJECT_DIR/data/intermediates/$EXPERIMENT_NAME/sparse"
DATABASE_PATH="$PROJECT_DIR/data/intermediates/$EXPERIMENT_NAME/database.db"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/colmap_pipeline.log"

mkdir -p "$IMAGES_DIR"
mkdir -p "$SPARSE_DIR"
mkdir -p "$LOG_DIR"

echo "========================================================="
echo "Starting COLMAP Pipeline for: $VIDEO_PATH"
echo "Project Directory: $PROJECT_DIR"
echo "Output logged to: $LOG_FILE"
echo "=========================================================" | tee "$LOG_FILE"

# --- Step 1: Extract Frames from Video ---
# Extracting 2 to 3 frames per second is usually ideal for tracking.
# Adjust 'fps=2' higher if your video camera moves very fast.
echo "--> Step 1: Extracting frames using ffmpeg..." | tee -a "$LOG_FILE"
# ffmpeg -i "$VIDEO_PATH" -vf "fps=2" -q:v 2 "$IMAGES_DIR/frame_%04d.jpg" 2>&1 | tee -a "$LOG_FILE"
ffmpeg -i "$VIDEO_PATH" -vf "mpdecimate=hi=64*12*1000:lo=64*5*0:frac=0.999" -vsync vfr -q:v 2 "$IMAGES_DIR/frame_%04d.jpg" 2>&1 | tee -a "$LOG_FILE"

# --- Step 2: Feature Extraction ---
# This locates unique points across your extracted frames
echo "--> Step 2: Extracting image features..." | tee -a "$LOG_FILE"
colmap feature_extractor \
    --database_path "$DATABASE_PATH" \
    --image_path "$IMAGES_DIR" \
    --ImageReader.camera_model "RADIAL" \
    --ImageReader.single_camera 1 \
    --ImageReader.default_focal_length_factor 1.2 \
    --FeatureExtraction.type "SIFT" \
    --FeatureExtraction.use_gpu 1 \
    --FeatureExtraction.gpu_index -1 \
    --SiftExtraction.max_num_features 4096 \
    --SiftExtraction.first_octave -1 \
    --SiftExtraction.num_octaves 4 \
    --SiftExtraction.octave_resolution 3 \
    --SiftExtraction.peak_threshold 0.00667 \
    --SiftExtraction.edge_threshold 20 \
    --SiftExtraction.estimate_affine_shape 0 \
    --SiftExtraction.max_num_orientations 2 \
    --SiftExtraction.upright 0 2>&1 | tee -a "$LOG_FILE"

# --- Step 3: Feature Matching ---
# Links corresponding features together. 'sequential' is ideal for video sequences
# where frames are ordered chronologically and adjacent frames are most relevant.
echo "--> Step 3: Matching features (Sequential)..." | tee -a "$LOG_FILE"
colmap sequential_matcher \
    --database_path "$DATABASE_PATH" \
    --FeatureMatching.type "SIFT_BRUTEFORCE" \
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
    --SequentialMatching.overlap 20 2>&1 | tee -a "$LOG_FILE"

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
    --Mapper.filter_max_reproj_error 8 \
    --Mapper.filter_min_tri_angle 1.5 \
    --Mapper.init_max_error 4 \
    --Mapper.init_min_tri_angle 16 \
    --Mapper.abs_pose_max_error 12 \
    --Mapper.abs_pose_min_num_inliers 30 2>&1 | tee -a "$LOG_FILE"

# --- Step 5: Distortion Correction ---
# Generates undistorted images and corrected camera poses for OpenSplat
echo "--> Step 5: Correcting camera distortion..." | tee -a "$LOG_FILE"
colmap image_undistorter \
    --image_path "$IMAGES_DIR" \
    --input_path "$SPARSE_DIR/0" \
    --output_path "${PROJECT_DIR}/data/intermediates/${EXPERIMENT_NAME}_distortion_corrected" \
    --output_type "COLMAP" \
    --copy_policy "copy" \
    --blank_pixels 0 \
    --min_scale 0.2 \
    --max_scale 2 \
    --max_image_size -1 \
    --num_patch_match_src_images 20 \
    --jpeg_quality -1 2>&1 | tee -a "$LOG_FILE"

echo "=========================================================" | tee -a "$LOG_FILE"
echo "COLMAP Pipeline complete!" | tee -a "$LOG_FILE"
echo "Your OpenSplat-ready dataset is located at:" | tee -a "$LOG_FILE"
echo "  $PROJECT_DIR/data/intermediates/${EXPERIMENT_NAME}_distortion_corrected/" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "=========================================================" | tee -a "$LOG_FILE"
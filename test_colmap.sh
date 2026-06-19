#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# --- Configuration ---
VIDEO_PATH="./data/incoming/gardenbed_test_4s_middle.mov"
PROJECT_DIR="/Users/bc/brendanchambers/2026-06-18-iphone-video-to-splat"
EXPERIMENT_NAME="test_4s"

if [ -z "$VIDEO_PATH" ] || [ -z "$PROJECT_DIR" ]; then
    echo "Usage: $0 <path_to_video.mov> <path_to_output_project_dir>"
    exit 1
fi

# Create directory structure expected by OpenSplat
IMAGES_DIR="$PROJECT_DIR/data/intermediates/$EXPERIMENT_NAME/images"
SPARSE_DIR="$PROJECT_DIR/data/intermediates/$EXPERIMENT_NAME/sparse"
DATABASE_PATH="$PROJECT_DIR/data/intermediates/$EXPERIMENT_NAME/database.db"

mkdir -p "$IMAGES_DIR"
mkdir -p "$SPARSE_DIR"

echo "========================================================="
echo "Starting COLMAP Pipeline for: $VIDEO_PATH"
echo "Project Directory: $PROJECT_DIR"
echo "Experiment: $EXPERIMENT_NAME"
echo "========================================================="

# --- Step 1: Extract Frames from Video ---
# Extracting 2 to 3 frames per second is usually ideal for tracking.
# Adjust 'fps=2' higher if your video camera moves very fast.
echo "--> Step 1: Extracting frames using ffmpeg..."
ffmpeg -i "$VIDEO_PATH" -vf "fps=2" -q:v 2 "$IMAGES_DIR/frame_%04d.jpg"

# --- Step 2: Feature Extraction ---
# This locates unique points across your extracted frames
echo "--> Step 2: Extracting image features..."
colmap feature_extractor \
    --database_path "$DATABASE_PATH" \
    --image_path "$IMAGES_DIR" \
    --ImageReader.camera_model "RADIAL" \
    --ImageReader.single_camera 1

# --- Step 3: Feature Matching ---
# Links corresponding features together. 'exhaustive' works best for video sequences
echo "--> Step 3: Matching features (Exhaustive)..."
colmap exhaustive_matcher \
    --database_path "$DATABASE_PATH"

# --- Step 4: Sparse Reconstruction ---
# Calculates camera locations and the 3D sparse point cloud
echo "--> Step 4: Generating 3D sparse reconstruction..."
colmap mapper \
    --database_path "$DATABASE_PATH" \
    --image_path "$IMAGES_DIR" \
    --output_path "$SPARSE_DIR"

# --- Step 5: Distortion Correction ---
# Creating undistorted poses for OpenSplat
echo "--> Step 5: Undistorting images and poses..."
DISTORTION_CORRECTED_DIR="${PROJECT_DIR}/data/intermediates/${EXPERIMENT_NAME}_distortion_corrected"
colmap image_undistorter \
    --image_path "$IMAGES_DIR" \
    --input_path "$SPARSE_DIR/0" \
    --output_path "$DISTORTION_CORRECTED_DIR" \
    --output_type COLMAP

echo "========================================================="
echo "Pipeline complete!"
echo "Distortion-corrected dataset is at: $DISTORTION_CORRECTED_DIR"
echo "========================================================="

#!/bin/bash
set -e

# Load environment variables
source "$(dirname "$0")/.env"

# Experiment configuration
EXPERIMENT_POSTFIX="_distortion_corrected"
FULL_EXPERIMENT_NAME="${EXPERIMENT_NAME}${EXPERIMENT_POSTFIX}"

# Path to compiled OpenSplat binary
OPENSPLAT_BIN="${PROJECT_DIR}/opensplat/build/opensplat"

# Define paths to COLMAP data and output folder
DATA_DIR="${PROJECT_DIR}/data/intermediates/${FULL_EXPERIMENT_NAME}/sparse"
IMAGES_DIR="${PROJECT_DIR}/data/intermediates/${FULL_EXPERIMENT_NAME}/images"
OUTPUT_DIR="${PROJECT_DIR}/data/intermediates/${FULL_EXPERIMENT_NAME}/opensplat_output"

echo "Starting OpenSplat training on M4 Metal GPU..."

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Execute OpenSplat (Adjust flags based on OpenSplat's CLI arguments)
$OPENSPLAT_BIN "$DATA_DIR" --colmap-image-path "$IMAGES_DIR" --output "$OUTPUT_DIR/scene.ply" --num-iters "$NUM_ITERS"

echo "Training complete! Output saved to $OUTPUT_DIR/scene.ply"

#### --- parameters in opensplat.cpp ---
#         ("i,input", "Path to nerfstudio project", cxxopts::value<std::string>())
#         ("o,output", "Path where to save output scene", cxxopts::value<std::string>()->default_value("splat.ply"))
#         ("s,save-every", "Save output scene every these many steps (set to -1 to disable)", cxxopts::value<int>()->default_value("-1"))
#         ("resume", "Resume training from this PLY file", cxxopts::value<std::string>()->default_value(""))
#         ("val", "Withhold a camera shot for validating the scene loss")
#         ("val-image", "Filename of the image to withhold for validating scene loss", cxxopts::value<std::string>()->default_value("random"))
#         ("val-render", "Path of the directory where to render validation images", cxxopts::value<std::string>()->default_value(""))
#         ("keep-crs", "Retain the project input's coordinate reference system")
#         ("cpu", "Force CPU execution")
        
#         ("n,num-iters", "Number of iterations to run", cxxopts::value<int>()->default_value("30000"))
#         ("d,downscale-factor", "Scale input images by this factor.", cxxopts::value<float>()->default_value("1"))
#         ("num-downscales", "Number of images downscales to use. After being scaled by [downscale-factor], images are initially scaled by a further (2^[num-downscales]) and the scale is increased every [resolution-schedule]", cxxopts::value<int>()->default_value("2"))
#         ("resolution-schedule", "Double the image resolution every these many steps", cxxopts::value<int>()->default_value("3000"))
#         ("sh-degree", "Maximum spherical harmonics degree (must be > 0)", cxxopts::value<int>()->default_value("3"))
#         ("sh-degree-interval", "Increase the number of spherical harmonics degree after these many steps (will not exceed [sh-degree])", cxxopts::value<int>()->default_value("1000"))
#         ("ssim-weight", "Weight to apply to the structural similarity loss. Set to zero to use least absolute deviation (L1) loss only", cxxopts::value<float>()->default_value("0.2"))
#         ("refine-every", "Split/duplicate/prune gaussians every these many steps", cxxopts::value<int>()->default_value("100"))
#         ("warmup-length", "Split/duplicate/prune gaussians only after these many steps", cxxopts::value<int>()->default_value("500"))
#         ("reset-alpha-every", "Reset the opacity values of gaussians after these many refinements (not steps)", cxxopts::value<int>()->default_value("30"))
#         ("densify-grad-thresh", "Threshold of the positional gradient norm (magnitude of the loss function) which when exceeded leads to a gaussian split/duplication", cxxopts::value<float>()->default_value("0.0002"))
#         ("densify-size-thresh", "Gaussians' scales below this threshold are duplicated, otherwise split", cxxopts::value<float>()->default_value("0.01"))
#         ("stop-screen-size-at", "Stop splitting gaussians that are larger than [split-screen-size] after these many steps", cxxopts::value<int>()->default_value("4000"))
#         ("split-screen-size", "Split gaussians that are larger than this percentage of screen space", cxxopts::value<float>()->default_value("0.05"))
#         ("colmap-image-path", "Override the default image path for COLMAP-based input", cxxopts::value<std::string>()->default_value(""))
# #ifdef USE_VISUALIZATION
#         ("has-visualization", "Show the visualization steps of training", cxxopts::value<bool>()->default_value("0"))
# #endif

#         ("h,help", "Print usage")
#         ("version", "Print version")
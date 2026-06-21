#!/bin/bash
cd "$(dirname "$0")/../.."
uv run python pipeline.py \
    --config-path config --config-name hparam_sweep_colmap \
     --multirun \
    colmap.feature_extraction.sift_max_num_features=4096,8192 \
    colmap.feature_extraction.sift_edge_threshold=10,20 \
    colmap.feature_matching.sequential_overlap=20,100 \
    colmap.mapper.filter_max_reproj_error=4,8

# max num features has biggest impact but also takes much longer to run. incrase for best results, use 4096 for now.

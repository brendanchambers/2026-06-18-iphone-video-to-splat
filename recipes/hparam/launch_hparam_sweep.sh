#!/bin/bash
cd "$(dirname "$0")/../.."
uv run python pipeline.py \
    --config-path config --config-name hparam_sweep \
     --multirun \
    opensplat.densify_size_thresh=0.00025,0.0025 \
    opensplat.densify_grad_thresh=0.00001,0.0001
    

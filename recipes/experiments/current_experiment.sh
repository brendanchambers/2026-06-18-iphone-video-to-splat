#!/bin/bash
cd "$(dirname "$0")/../.."  # go to project root if necessary
uv run python pipeline.py --config-path config --config-name more_gaussians "$@"

uv run python pipeline.py --config-path config --config-name baseline "$@"

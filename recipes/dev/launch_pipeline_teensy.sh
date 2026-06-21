#!/bin/bash
cd "$(dirname "$0")/../.."
uv run python pipeline.py --config-path config --config-name teensy "$@"
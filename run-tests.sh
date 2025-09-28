#!/usr/bin/env bash
set -euo pipefail

# Install test dependencies with version pinning for reproducibility
apk add --no-cache python3=3.11.9-r0 py3-pip=23.1.2-r0
pip3 install pytest==7.4.4 --break-system-packages

# Run the tests
pytest -q tests/test_outputs.py -v

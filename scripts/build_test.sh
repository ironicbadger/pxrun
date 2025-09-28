#!/bin/bash
# Script to build and test the pxrun package locally using uv

set -e

echo "Building and testing pxrun package with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/ .eggs/

# Build the package with uv
echo "Building package..."
uv build

# Check the package with twine via uvx
echo "Checking package with twine..."
uvx twine check dist/*

# Install in a test environment
echo "Creating test virtual environment..."
uv venv test_env
source test_env/bin/activate

echo "Installing package in test environment..."
uv pip install dist/*.whl

# Test the installed package
echo "Testing installed package..."
pxrun --version
pxrun --help

# Clean up test environment
deactivate
rm -rf test_env

echo "Build test completed successfully!"
echo ""
echo "Package files created:"
ls -lh dist/
echo ""
echo "To install locally: uv pip install dist/*.whl"
echo "To upload to PyPI: ./scripts/publish.sh"
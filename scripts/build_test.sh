#!/bin/bash
# Script to build and test the pxrun package locally

set -e

echo "Building and testing pxrun package..."

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/ .eggs/

# Ensure we have the latest build tools
echo "Installing build tools..."
pip install --quiet --upgrade pip setuptools wheel build twine

# Build the package
echo "Building package..."
python -m build

# Check the package
echo "Checking package with twine..."
twine check dist/*

# Install in a test environment
echo "Creating test virtual environment..."
python3 -m venv test_env
source test_env/bin/activate

echo "Installing package in test environment..."
pip install --quiet dist/*.whl

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
echo "To install locally: pip install dist/*.whl"
echo "To upload to PyPI: ./scripts/publish.sh"
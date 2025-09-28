#!/bin/bash
# Script to publish pxrun to PyPI using uv (modern Python packaging)

set -e

echo "Publishing pxrun to PyPI using uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/

# Build the package with uv
echo "Building package with uv..."
uv build

# Check the package
echo "Checking package..."
uvx twine check dist/*

# Upload to Test PyPI first (optional)
read -p "Upload to Test PyPI first? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Uploading to Test PyPI..."
    uvx twine upload --repository-url https://test.pypi.org/legacy/ dist/*
    echo "Package uploaded to Test PyPI"
    echo "Test install with: uv pip install --index-url https://test.pypi.org/simple/ pxrun"
    read -p "Continue to production PyPI? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]
    then
        echo "Aborted production upload."
        exit 0
    fi
fi

# Upload to PyPI
echo "Uploading to PyPI..."
uvx twine upload dist/*

echo "Successfully published pxrun to PyPI!"
echo "Install with: uv pip install pxrun"
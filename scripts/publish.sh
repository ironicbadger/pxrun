#!/bin/bash
# Script to publish pxrun to PyPI

set -e

echo "Publishing pxrun to PyPI..."

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/

# Ensure we have the latest build tools
echo "Upgrading build tools..."
pip install --upgrade pip setuptools wheel twine build

# Build the package
echo "Building package..."
python -m build

# Check the package
echo "Checking package with twine..."
twine check dist/*

# Upload to Test PyPI first (optional)
read -p "Upload to Test PyPI first? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Uploading to Test PyPI..."
    twine upload --repository-url https://test.pypi.org/legacy/ dist/*
    echo "Package uploaded to Test PyPI"
    echo "Test install with: pip install --index-url https://test.pypi.org/simple/ pxrun"
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
twine upload dist/*

echo "Successfully published pxrun to PyPI!"
echo "Install with: pip install pxrun"
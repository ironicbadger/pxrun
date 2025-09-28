#!/bin/bash
# Setup Python virtual environment for local development

set -e

VENV_DIR=".venv"
PYTHON_VERSION="3.11"

echo "🐍 Setting up Python virtual environment..."

# Check if Python 3.11 is available
if ! command -v python${PYTHON_VERSION} &> /dev/null; then
    echo "❌ Python ${PYTHON_VERSION} is not installed"
    echo "Please install Python ${PYTHON_VERSION} first"
    exit 1
fi

# Remove existing venv if it exists
if [ -d "$VENV_DIR" ]; then
    echo "Removing existing virtual environment..."
    rm -rf "$VENV_DIR"
fi

# Create new virtual environment
echo "Creating virtual environment with Python ${PYTHON_VERSION}..."
python${PYTHON_VERSION} -m venv "$VENV_DIR"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip and install wheel
echo "Upgrading pip and installing wheel..."
pip install --upgrade pip setuptools wheel

# Install development dependencies
echo "Installing development dependencies..."
pip install -r requirements-dev.txt

# Install package in editable mode
echo "Installing pxrun in editable mode..."
pip install -e .

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install

echo "✅ Virtual environment setup complete!"
echo ""
echo "To activate the environment, run:"
echo "  source ${VENV_DIR}/bin/activate"
echo ""
echo "To deactivate, run:"
echo "  deactivate"
#!/bin/bash
# Setup Python virtual environment for local development using uv

set -e

VENV_DIR=".venv"
PYTHON_VERSION="3.11"

echo "🐍 Setting up Python virtual environment with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

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

# Create new virtual environment with uv
echo "Creating virtual environment with Python ${PYTHON_VERSION}..."
uv venv "$VENV_DIR" --python python${PYTHON_VERSION}

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install development dependencies with uv
echo "Installing development dependencies..."
uv pip install -r requirements-dev.txt

# Install package in editable mode
echo "Installing pxrun in editable mode..."
uv pip install -e .

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
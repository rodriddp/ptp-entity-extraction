#!/bin/bash

# Define environment name and Python version
ENV_NAME=".ptp-entity-extraction"
PYTHON_COMMAND="python3"

# Create virtual environment
$PYTHON_COMMAND -m venv $ENV_NAME

# Activate the environment
source $ENV_NAME/Scripts/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r utils/env_setup/requirements.txt

echo "✅ Environment '$ENV_NAME' created and dependencies installed."

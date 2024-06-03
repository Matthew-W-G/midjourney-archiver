#!/bin/bash

# Navigate to the project directory
cd /Users/matthewgiuliano/Desktop/MidjourneyArchiverV3

#rm -rf myenv

# Create a virtual environment if it does not exist
if [ ! -d "myenv" ]; then
  python3 -m venv myenv
fi

# Activate the virtual environment
source myenv/bin/activate

# Print paths for debugging
which python
which pip

# Upgrade pip
python3 -m pip install --upgrade pip

# Install the required packages
python3 -m pip install -r requirements.txt

# Install playwright browsers
python3 -m playwright install

# Source environment variables from .env file
set -o allexport
source .env
set
set +o allexport

# Check if the variable is passed as an argument, otherwise set it to 100
if [ -z "$1" ]; then
    LIMIT=150
else
    LIMIT=$1
fi

# Print the limit for debugging
echo "Running script with limit: $LIMIT"

# Set the PYTHONPATH to the project root
export PYTHONPATH=$(pwd)/src

# Run the scraping script
python3 src/scripts/run_scraper.py "$LIMIT"

# Deactivate the virtual environment
deactivate

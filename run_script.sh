# Navigate to the project directory
cd /Users/matthewgiuliano/Desktop/MidjourneyArchiverV3

# Create a virtual environment if it does not exist
python3 -m venv myenv

# Activate the virtual environment
source myenv/bin/activate

# Print paths for debugging
which python
which pip

# Upgrade pip
python3 -m pip install --upgrade pip

# Install the required packages
python3 -m pip install -r requirements.txt

# List installed packages
python3 -m pip list

#Install playwright browsers
python -m playwright install

# Check if the variable is passed as an argument
if [ -z "$1" ]; then
  echo "Usage: $0 <variable>"
  exit 1
fi

# assign first argument to limit var
LIMIT=$1

# Run the Python script
python3 archiveScraper.py "$LIMIT"

# Deactivate the virtual environment
deactivate

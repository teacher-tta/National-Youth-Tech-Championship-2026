#!/bin/zsh
set -e

PROJECT_PARENT="$HOME/Desktop"
REPO_URL="https://github.com/teacher-tta/National-Youth-Tech-Championship-2026"
REPO_NAME="National-Youth-Tech-Championship-2026"
VENV_NAME="venv"

echo "Checking internet connection..."
if ! ping -c 1 -t 5 8.8.8.8 >/dev/null 2>&1; then
    echo ""
    echo "ERROR: No internet connection detected."
    echo "Please check your network connection and run this script again."
    echo ""
    exit 1
fi
echo "Internet connection OK."

echo "Checking for Homebrew..."

if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || {
        echo ""
        echo "ERROR: Failed to install Homebrew."
        echo "This may be caused by a lost internet connection or the server being unreachable."
        echo "Please check your connection and try again."
        echo ""
        exit 1
    }

    if [[ -d "/opt/homebrew/bin" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        eval "$(/usr/local/bin/brew shellenv)"
    fi
else
    echo "Homebrew already installed."
fi

echo "Updating Homebrew..."
brew update || {
    echo ""
    echo "WARNING: Failed to update Homebrew."
    echo "Your internet connection may have been interrupted."
    echo "Please check your connection and run this script again."
    echo ""
    exit 1
}

echo "Installing dependencies (python)..."
brew install python@3.13 || {
    echo ""
    echo "ERROR: Failed to install Python 3.13 via Homebrew."
    echo "This may be caused by a lost internet connection during download."
    echo "Please check your connection and run this script again."
    echo ""
    exit 1
}

PYTHON_BIN=$(brew --prefix python@3.13)/bin/python3.13

echo "Moving to Desktop..."
cd "$PROJECT_PARENT"

echo "Downloading repository as ZIP..."
if [ ! -d "$REPO_NAME" ]; then
    curl -L "$REPO_URL/archive/refs/heads/main.zip" -o "$REPO_NAME.zip" || {
        echo ""
        echo "ERROR: Failed to download repository."
        echo "This may be caused by a lost internet connection or the server being unreachable."
        echo "Please check your connection and try again."
        echo ""
        exit 1
    }
    unzip "$REPO_NAME.zip"
    mv "$REPO_NAME-main" "$REPO_NAME"
    rm "$REPO_NAME.zip"
else
    echo "Repository folder already exists. Skipping download."
fi

echo "Entering repository folder..."
cd "$REPO_NAME"

echo "Creating requirements.txt..."

cat <<EOF > requirements.txt
ugot
opencv-python
ipykernel
ipython
ultralytics
EOF

echo "Creating virtual environment..."
"$PYTHON_BIN" -m venv "$VENV_NAME"

echo "Activating virtual environment..."
source "$VENV_NAME/bin/activate"

echo "Upgrading pip..."
python -m pip install --upgrade pip || {
    echo ""
    echo "WARNING: Failed to upgrade pip."
    echo "Your internet connection may have been interrupted."
    echo "Please check your connection and run this script again."
    echo ""
    exit 1
}

echo "Installing dependencies..."
python -m pip install -r requirements.txt || {
    echo ""
    echo "ERROR: Failed to install one or more packages."
    echo "This is often caused by a lost internet connection during download."
    echo ""
    echo "Please check your connection and run this script again."
    echo "The virtual environment will be reused, so already-downloaded"
    echo "packages will not need to be re-downloaded."
    echo ""
    exit 1
}

echo "-----------------------------------------------"
echo ""
echo "Setup complete!"
echo "Project located at:"
echo "$PROJECT_PARENT/$REPO_NAME"
echo ""

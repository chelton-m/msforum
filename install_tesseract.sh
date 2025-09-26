#!/bin/bash

# Tesseract OCR Installation Script for macOS

echo "Installing Tesseract OCR for CAPTCHA reading..."
echo "=============================================="

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Homebrew not found. Installing Homebrew first..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ $(uname -m) == "arm64" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
fi

# Install Tesseract
echo "Installing Tesseract OCR..."
brew install tesseract

# Verify installation
if command -v tesseract &> /dev/null; then
    echo "✅ Tesseract installed successfully!"
    echo "Version: $(tesseract --version | head -n1)"
    echo ""
    echo "Tesseract is now ready for CAPTCHA reading."
else
    echo "❌ Tesseract installation failed."
    exit 1
fi

echo ""
echo "Installation complete! You can now run the bot with automatic CAPTCHA reading."

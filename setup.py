#!/usr/bin/env python3
"""
Setup script for Costco Receipt Price Tracker
"""

import os
import sys
import subprocess
import platform

def check_python_version():
    """Check if Python version is 3.8+"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required. Current version:", sys.version)
        return False
    print("✅ Python version:", sys.version.split()[0])
    return True

def check_tesseract():
    """Check if Tesseract is installed"""
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print("✅ Tesseract found:", version)
            return True
    except FileNotFoundError:
        pass
    
    print("❌ Tesseract OCR not found!")
    print_tesseract_instructions()
    return False

def print_tesseract_instructions():
    """Print Tesseract installation instructions"""
    system = platform.system().lower()
    
    print("\n📋 Tesseract Installation Instructions:")
    
    if system == "darwin":  # macOS
        print("  For macOS (using Homebrew):")
        print("    brew install tesseract")
    elif system == "linux":
        print("  For Ubuntu/Debian:")
        print("    sudo apt-get update")
        print("    sudo apt-get install tesseract-ocr")
        print("  For CentOS/RHEL:")
        print("    sudo yum install tesseract")
    elif system == "windows":
        print("  For Windows:")
        print("    Download from: https://github.com/UB-Mannheim/tesseract/wiki")
    else:
        print("  Please install Tesseract OCR for your operating system")
    
    print("  After installation, restart your terminal and run this script again.")

def install_requirements():
    """Install Python requirements"""
    print("\n📦 Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ['uploads', 'static']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Created directory: {directory}")

def run_application():
    """Run the Flask application"""
    print("\n🚀 Starting Costco Receipt Price Tracker...")
    print("📱 Open your browser and navigate to: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the server")
    
    try:
        subprocess.run([sys.executable, 'app.py'])
    except KeyboardInterrupt:
        print("\n👋 Application stopped.")

def main():
    """Main setup function"""
    print("🎯 Costco Receipt Price Tracker Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check Tesseract
    if not check_tesseract():
        sys.exit(1)
    
    # Install requirements
    if not install_requirements():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    print("\n✅ Setup completed successfully!")
    
    # Ask user if they want to run the application
    response = input("\n🤔 Would you like to start the application now? (y/n): ").lower().strip()
    if response in ['y', 'yes']:
        run_application()
    else:
        print("\n🎉 Setup complete! Run 'python app.py' to start the application.")
        print("📖 See README.md for more information.")

if __name__ == "__main__":
    main() 
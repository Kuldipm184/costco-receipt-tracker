#!/usr/bin/env python3
"""
Costco Receipt Tracker - Startup Script

This script handles environment setup and launches the application.
"""

import os
import sys
from dotenv import load_dotenv

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import flask
        import openai
        print("✓ All required dependencies are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_api_key():
    """Check if OpenAI API key is set"""
    # Load environment variables from .env file
    load_dotenv()
    
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("✗ OPENAI_API_KEY environment variable is not set")
        print("\nTo set up your API key, you can:")
        print("1. Create a .env file in this directory with:")
        print("   OPENAI_API_KEY=your-api-key-here")
        print("2. Or get your API key from: https://platform.openai.com/api-keys")
        print("3. Or set it as environment variable:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        return False
    else:
        # Hide most of the key for security
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"✓ OpenAI API key is set: {masked_key}")
        return True

def main():
    """Main startup function"""
    print("🏪 Costco Receipt Tracker - OpenAI Vision Powered")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check API key
    if not check_api_key():
        print("\n❌ Cannot start without OpenAI API key")
        sys.exit(1)
    
    print("\n🚀 Starting application...")
    print("📱 Access the app at: http://localhost:5002")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Import and run the Flask app
    try:
        from app import app, db
        
        # Create database tables if they don't exist
        with app.app_context():
            db.create_all()
            print("✓ Database initialized")
        
        # Start the Flask application
        port = int(os.environ.get('PORT', 5002))
        debug = os.environ.get('DEBUG', 'False').lower() == 'true'
        
        app.run(
            debug=debug,
            host='0.0.0.0',
            port=port
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 Application stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
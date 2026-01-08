#!/usr/bin/env python3
"""
Simple script to run the web server
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.web.app import app

if __name__ == '__main__':
    print("🚀 Starting YC Insight Extractor Web Interface")
    print("=" * 60)
    print(f"📁 Project root: {PROJECT_ROOT}")
    print(f"🌐 Server: http://localhost:5012")
    print("=" * 60)
    print("Press Ctrl+C to stop")
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5012)

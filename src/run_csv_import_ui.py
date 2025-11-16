#!/usr/bin/env python3
"""
Launcher for the CSV Import Web UI.
Opens browser automatically when server starts.
"""

import os
import sys
import time
import webbrowser
import threading
from pathlib import Path

BASE_DIR = Path(__file__).parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from csv_import_server import app, socketio, logger


def open_browser():
    """Open browser after a short delay to allow server startup."""
    time.sleep(2)
    try:
        webbrowser.open('http://localhost:5000')
        logger.info("Browser opened at http://localhost:5000")
    except Exception as e:
        logger.error(f"Could not open browser: {e}")
        logger.info("Please manually navigate to http://localhost:5000")


def main():
    """Run the import server."""
    logger.info("="*70)
    logger.info("CSV Import Web UI - Starting Server")
    logger.info("="*70)
    logger.info("")
    logger.info("Server will be available at: http://localhost:5000")
    logger.info("")
    logger.info("Features:")
    logger.info("  [+] Fast batch CSV import (2000 records/batch)")
    logger.info("  [+] Real-time progress tracking")
    logger.info("  [+] Automatic grouping table lookup (indexed)")
    logger.info("  [+] Web-based UI with live statistics")
    logger.info("  [+] Batch grouping updates")
    logger.info("")
    logger.info("="*70)
    
    # Open browser in separate thread
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Run the Flask app
    socketio.run(
        app,
        host='127.0.0.1',
        port=5000,
        debug=False,
        allow_unsafe_werkzeug=True,
        use_reloader=False
    )


if __name__ == '__main__':
    main()

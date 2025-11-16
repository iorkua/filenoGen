#!/usr/bin/env python3
"""
Modern web UI for CSV import with real-time progress updates using WebSockets.
"""

import os
import sys
import json
import threading
import logging
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, disconnect

BASE_DIR = Path(__file__).parent
PARENT_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from fast_csv_importer import FastCSVImporter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
import_thread = None
active_importer = None
import_lock = threading.Lock()


def progress_callback(message: str, progress: float = None):
    """Callback to send progress updates via WebSocket."""
    try:
        data = {
            'message': message,
            'progress': progress if progress is not None else None,
            'timestamp': datetime.now().isoformat()
        }
        socketio.emit('progress', data, to=None)
        logger.info(f"Progress: {message} ({progress}%)" if progress is not None else f"Progress: {message}")
    except Exception as e:
        logger.error(f"Error sending progress: {e}")


def run_import_thread(csv_path: str, control_tag: str):
    """Run import in background thread."""
    global active_importer
    
    try:
        with import_lock:
            active_importer = FastCSVImporter()
            active_importer.set_progress_callback(progress_callback)
        
        csv_file = Path(csv_path).expanduser().resolve()
        
        if not csv_file.exists():
            socketio.emit('error', {'message': f'CSV file not found: {csv_path}'}, broadcast=True)
            return
        
        success = active_importer.run_import(csv_file, control_tag)
        
        result = {
            'success': success,
            'total_records': active_importer.total_records,
            'inserted_records': active_importer.inserted_records,
            'matched_records': active_importer.matched_records,
            'unmatched_records': active_importer.unmatched_records,
            'skipped_records': active_importer.skipped_records
        }
        
        socketio.emit('import_complete', result, to=None)
        
    except Exception as e:
        logger.error(f"Import thread error: {e}")
        socketio.emit('error', {'message': str(e)}, to=None)
    finally:
        with import_lock:
            active_importer = None


@app.route('/')
def index():
    """Serve the main UI page."""
    return render_template('import_ui.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get default configuration."""
    return jsonify({
        'csv_file': 'FileNos_PRO.csv',
        'control_tag': 'PROD',
        'batch_size': 2000
    })


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info('Client connected')
    emit('status', {'data': 'Connected to import server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info('Client disconnected')


@socketio.on('start_import')
def handle_start_import(data):
    """Handle import start request."""
    global import_thread, active_importer
    
    with import_lock:
        if import_thread and import_thread.is_alive():
            emit('error', {'message': 'Import already in progress'})
            return
        
        csv_file = data.get('csv_file', 'FileNos_PRO.csv')
        control_tag = data.get('control_tag', 'PROD')
        
        logger.info(f"Starting import: {csv_file} with tag: {control_tag}")
        emit('import_started', {'csv_file': csv_file, 'control_tag': control_tag}, broadcast=True)
        
        import_thread = threading.Thread(
            target=run_import_thread,
            args=(csv_file, control_tag),
            daemon=True
        )
        import_thread.start()


@socketio.on('cancel_import')
def handle_cancel_import():
    """Handle import cancellation request."""
    global active_importer
    
    with import_lock:
        if active_importer:
            logger.info("Cancellation requested by user")
            active_importer.request_cancel()
            emit('import_cancelled', {'message': 'Cancellation requested'}, broadcast=True)
        else:
            emit('error', {'message': 'No active import to cancel'})


@socketio.on('get_status')
def handle_get_status():
    """Get current import status."""
    global active_importer
    
    with import_lock:
        if active_importer:
            status = {
                'running': True,
                'total_records': active_importer.total_records,
                'processed_records': active_importer.processed_records,
                'inserted_records': active_importer.inserted_records,
                'matched_records': active_importer.matched_records,
                'unmatched_records': active_importer.unmatched_records,
                'skipped_records': active_importer.skipped_records
            }
        else:
            status = {'running': False}
        
        emit('status_update', status)


def main():
    """Run the Flask app."""
    logger.info("Starting CSV Import Web UI...")
    logger.info("Open your browser to http://localhost:5000")
    socketio.run(app, host='127.0.0.1', port=5000, debug=True, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()

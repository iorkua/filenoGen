#!/usr/bin/env python3
"""Chunked CSV import server with queued uploads and real-time updates."""

import os
import sys
import json
import csv
import copy
import logging
import threading
from uuid import uuid4
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).parent
PARENT_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from fast_csv_importer import FastCSVImporter

# Configuration
UPLOAD_DIR = PARENT_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
JOBS_FILE = UPLOAD_DIR / "jobs.json"
MAX_ROWS_PER_FILE = 1000

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask / Socket.IO setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")


class JobManager:
    """Manage upload jobs with simple JSON persistence."""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.jobs = []
        self.lock = threading.Lock()
        self._load_jobs()

    def _load_jobs(self) -> None:
        if not self.storage_path.exists():
            self.jobs = []
            return

        try:
            with self.storage_path.open('r', encoding='utf-8') as handle:
                self.jobs = json.load(handle)
        except json.JSONDecodeError as exc:
            logger.warning("Failed to load jobs storage: %s", exc)
            self.jobs = []

        # Reset any running jobs back to pending on restart
        restart_time = datetime.now().isoformat()
        for job in self.jobs:
            if job.get('status') == 'running':
                job['status'] = 'pending'
                job['started_at'] = None
                job['finished_at'] = None
                job['progress'] = 0.0
                job['last_message'] = 'Reset to pending after restart'
                job['updated_at'] = restart_time

    def _save_jobs(self) -> None:
        with self.storage_path.open('w', encoding='utf-8') as handle:
            json.dump(self.jobs, handle, indent=2)

    def list_jobs(self) -> List[Dict[str, Any]]:
        with self.lock:
            return copy.deepcopy(self.jobs)

    def add_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            self.jobs.append(job)
            self._save_jobs()
            return copy.deepcopy(job)

    def update_job(self, job_id: str, updates: Dict[str, Any], persist: bool = True) -> Optional[Dict[str, Any]]:
        with self.lock:
            for job in self.jobs:
                if job['id'] == job_id:
                    job.update(updates)
                    job['updated_at'] = datetime.now().isoformat()
                    if persist:
                        self._save_jobs()
                    return copy.deepcopy(job)
        return None

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            for job in self.jobs:
                if job['id'] == job_id:
                    return copy.deepcopy(job)
        return None

    def get_next_pending(self) -> Optional[Dict[str, Any]]:
        with self.lock:
            for job in self.jobs:
                if job.get('status') == 'pending':
                    job['status'] = 'queued'
                    job['updated_at'] = datetime.now().isoformat()
                    self._save_jobs()
                    return copy.deepcopy(job)
        return None


job_manager = JobManager(JOBS_FILE)
import_thread = None
import_lock = threading.Lock()
active_importer: Optional[FastCSVImporter] = None
active_job_id: Optional[str] = None


def broadcast_jobs_update() -> None:
    socketio.emit('jobs_update', {'jobs': job_manager.list_jobs()}, to=None)


def set_job_progress(job_id: str, message: str, progress: float | None) -> None:
    updated = job_manager.update_job(
        job_id,
        {
            'last_message': message,
            'progress': float(progress) if progress is not None else None
        },
        persist=False
    )
    if updated:
        broadcast_jobs_update()


def progress_callback(message: str, progress: float | None = None) -> None:
    """Forward importer progress to web clients and update job state."""
    try:
        payload = {
            'message': message,
            'progress': progress if progress is not None else None,
            'timestamp': datetime.now().isoformat(),
            'job_id': active_job_id
        }
        if active_job_id:
            set_job_progress(active_job_id, message, progress)
        socketio.emit('progress', payload, to=None)
        if progress is not None:
            logger.info("Progress[%s]: %s (%.1f%%)", active_job_id, message, progress)
        else:
            logger.info("Progress[%s]: %s", active_job_id, message)
    except Exception as exc:
        logger.error("Error sending progress: %s", exc)


def start_next_job() -> None:
    global import_thread

    with import_lock:
        if import_thread and import_thread.is_alive():
            return

        next_job = job_manager.get_next_pending()
        if not next_job:
            return

        job_manager.update_job(
            next_job['id'],
            {
                'status': 'running',
                'started_at': datetime.now().isoformat(),
                'progress': 0.0,
                'last_message': 'Starting import...'
            }
        )
        broadcast_jobs_update()

        import_thread = threading.Thread(
            target=process_job,
            args=(next_job['id'],),
            daemon=True
        )
        import_thread.start()


def process_job(job_id: str) -> None:
    """Run the importer for a queued job."""
    global active_importer, active_job_id

    job = job_manager.get_job(job_id)
    if not job:
        logger.error("Job %s not found", job_id)
        return

    csv_path = UPLOAD_DIR / job['stored_name']
    if not csv_path.exists():
        logger.error("Job file missing: %s", csv_path)
        job_manager.update_job(job_id, {'status': 'error', 'error': 'CSV file missing'})
        broadcast_jobs_update()
        start_next_job()
        return

    try:
        active_job_id = job_id
        with import_lock:
            active_importer = FastCSVImporter()
            active_importer.set_progress_callback(progress_callback)

        success = active_importer.run_import(csv_path, job.get('control_tag') or 'PROD')

        stats = {
            'total_records': active_importer.total_records,
            'inserted_records': active_importer.inserted_records,
            'matched_records': active_importer.matched_records,
            'unmatched_records': active_importer.unmatched_records,
            'skipped_records': active_importer.skipped_records,
            'duplicate_records': active_importer.duplicate_records
        }

        if success:
            job_manager.update_job(
                job_id,
                {
                    'status': 'completed',
                    'finished_at': datetime.now().isoformat(),
                    'progress': 100.0,
                    'last_message': 'Import completed',
                    'stats': stats,
                    'error': None
                }
            )
        else:
            job_manager.update_job(
                job_id,
                {
                    'status': 'error',
                    'finished_at': datetime.now().isoformat(),
                    'last_message': 'Import failed',
                    'stats': stats,
                    'error': 'Import did not complete successfully'
                }
            )

        socketio.emit(
            'import_complete',
            {
                'job_id': job_id,
                'success': success,
                **stats,
                'control_tag': job.get('control_tag'),
                'file_name': job.get('original_name')
            },
            to=None
        )

    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        job_manager.update_job(
            job_id,
            {
                'status': 'error',
                'finished_at': datetime.now().isoformat(),
                'last_message': 'Import failed',
                'error': str(exc)
            }
        )
        socketio.emit('error', {'message': str(exc), 'job_id': job_id}, to=None)

    finally:
        with import_lock:
            active_importer = None
        active_job_id = None
        broadcast_jobs_update()
        start_next_job()


def count_rows(csv_path: Path) -> int:
    """Return the number of non-empty data rows in the CSV file."""
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
    for encoding in encodings:
        try:
            with csv_path.open('r', encoding=encoding, newline='') as handle:
                reader = csv.reader(handle)
                next(reader, None)  # skip header
                return sum(1 for row in reader if any(cell.strip() for cell in row))
        except UnicodeDecodeError:
            continue
    raise ValueError('Unable to decode CSV file with supported encodings')


def validate_row_limit(csv_path: Path) -> int:
    row_count = count_rows(csv_path)
    if row_count == 0:
        raise ValueError('CSV file does not contain any data rows')
    if row_count > MAX_ROWS_PER_FILE:
        raise ValueError(f'CSV contains {row_count} rows. Maximum allowed is {MAX_ROWS_PER_FILE}.')
    return row_count


@app.route('/')
def index():
    return render_template('import_ui.html')


@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    return jsonify({'jobs': job_manager.list_jobs(), 'max_rows_per_file': MAX_ROWS_PER_FILE})


@app.route('/api/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    upload = request.files['file']
    if upload.filename == '':
        return jsonify({'error': 'Uploaded file has no name'}), 400

    control_tag = request.form.get('controlTag', 'PROD').strip() or 'PROD'
    original_name = upload.filename
    safe_name = secure_filename(original_name) or f'upload_{uuid4().hex}.csv'
    stored_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex}_{safe_name}"
    target_path = UPLOAD_DIR / stored_name

    upload.save(target_path)

    try:
        row_count = validate_row_limit(target_path)
    except Exception as exc:
        target_path.unlink(missing_ok=True)
        return jsonify({'error': str(exc)}), 400

    job = {
        'id': uuid4().hex,
        'original_name': original_name,
        'stored_name': stored_name,
        'row_count': row_count,
        'control_tag': control_tag,
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'started_at': None,
        'finished_at': None,
        'progress': 0.0,
        'last_message': 'Pending import',
        'stats': None,
        'error': None
    }

    job_manager.add_job(job)
    broadcast_jobs_update()
    start_next_job()

    return jsonify({'job': job, 'message': 'File queued for import'}), 201


@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    emit('status', {'data': 'Connected to import server'})
    emit('jobs_update', {'jobs': job_manager.list_jobs()})


@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')


@socketio.on('get_status')
def handle_get_status():
    emit(
        'status_update',
        {
            'running': active_job_id is not None,
            'active_job_id': active_job_id,
            'jobs': job_manager.list_jobs()
        }
    )


def main():
    logger.info("Starting CSV Import Web UI...")
    logger.info("Open your browser to http://localhost:5000")
    start_next_job()
    socketio.run(app, host='127.0.0.1', port=5000, debug=True, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()

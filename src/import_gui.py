import sys
import threading
import queue
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from typing import Optional

BASE_DIR = Path(__file__).parent
PARENT_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from excel_importer import ExcelImporter


class ImportApp(tk.Tk):
    """Tkinter UI for running the Excel importer with progress monitoring."""

    def __init__(self):
        super().__init__()
        self.title("File Number Importer")
        self.geometry("900x600")
        self.message_queue: queue.Queue = queue.Queue()
        self.import_thread: Optional[threading.Thread] = None
        self.active_importer: Optional[ExcelImporter] = None
        self.current_operation: Optional[str] = None

        self.progress_var = tk.DoubleVar(value=0.0)
        self.status_var = tk.StringVar(value="Idle")

        self._build_ui()
        self.after(100, self._process_queue)

    def _build_ui(self) -> None:
        main_frame = ttk.Frame(self, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(file_frame, text="Excel file:").pack(side=tk.LEFT)
        self.file_entry = ttk.Entry(file_frame)
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))
        default_excel = PARENT_DIR / "FileNos_PRO.xlsx"
        if default_excel.exists():
            self.file_entry.insert(0, str(default_excel.resolve()))
        browse_button = ttk.Button(file_frame, text="Browse…", command=self._browse_file)
        browse_button.pack(side=tk.LEFT)

        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(options_frame, text="Row limit (0 = all):").grid(row=0, column=0, sticky=tk.W)
        self.row_limit_entry = ttk.Entry(options_frame, width=10)
        self.row_limit_entry.insert(0, "0")
        self.row_limit_entry.grid(row=0, column=1, sticky=tk.W, padx=(6, 20))

        ttk.Label(options_frame, text="Control tag:").grid(row=0, column=2, sticky=tk.W)
        self.control_entry = ttk.Entry(options_frame, width=15)
        self.control_entry.insert(0, "PROD")
        self.control_entry.grid(row=0, column=3, sticky=tk.W)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 12))

        self.start_button = ttk.Button(button_frame, text="Start Import", command=self._start_import)
        self.start_button.pack(side=tk.LEFT)

        self.cleanup_button = ttk.Button(button_frame, text="Cleanup Tagged Records", command=self._start_cleanup)
        self.cleanup_button.pack(side=tk.LEFT, padx=(8, 0))

        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self._cancel_import, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=(8, 0))

        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X)

        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, expand=True)

        self.progress_label = ttk.Label(progress_frame, text="0.0%")
        self.progress_label.pack(anchor=tk.E, pady=(4, 0))

        self.status_label = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_label.pack(fill=tk.X, pady=(8, 4))

        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=20, state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _browse_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select Excel file",
            filetypes=(("Excel Files", "*.xlsx"), ("All Files", "*.*"))
        )
        if file_path:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, file_path)

    def _start_import(self) -> None:
        if self.import_thread and self.import_thread.is_alive():
            messagebox.showinfo("Import Running", "An import is already in progress.")
            return

        excel_path = Path(self.file_entry.get().strip())
        if not excel_path.exists():
            messagebox.showerror("File Not Found", "Please select a valid Excel file.")
            return

        row_limit_input = self.row_limit_entry.get().strip()
        try:
            row_limit = int(row_limit_input) if row_limit_input else 0
        except ValueError:
            messagebox.showerror("Invalid Row Limit", "Row limit must be an integer value.")
            return

        control_tag = self.control_entry.get().strip()

        self._reset_progress()
        self._set_running_state(True)
        self.current_operation = "import"
        self._append_log("Starting import...")

        self.import_thread = threading.Thread(
            target=self._run_import_thread,
            args=(excel_path, row_limit, control_tag),
            daemon=True
        )
        self.import_thread.start()

    def _start_cleanup(self) -> None:
        if self.import_thread and self.import_thread.is_alive():
            messagebox.showinfo("Operation Running", "Please wait for the current operation to finish.")
            return

        control_tag = self.control_entry.get().strip()
        if not control_tag:
            messagebox.showerror("Missing Control Tag", "Please provide the control tag to clean up.")
            return

        self._reset_progress()
        self._set_running_state(True, allow_cancel=False)
        self.current_operation = "cleanup"
        self._append_log("Starting cleanup...")

        self.import_thread = threading.Thread(
            target=self._run_cleanup_thread,
            args=(control_tag,),
            daemon=True
        )
        self.import_thread.start()

    def _cancel_import(self) -> None:
        if self.active_importer:
            self.active_importer.request_cancel()
            self.cancel_button.config(state=tk.DISABLED)
            self._append_log("Cancellation requested. Waiting for importer to stop...")
        else:
            self._append_log("No active import to cancel.")

    def _run_import_thread(self, excel_path: Path, row_limit: int, control_tag: str) -> None:
        try:
            importer = ExcelImporter()
            importer.set_progress_callback(self._queue_progress)
            importer.excel_file_path = excel_path
            importer.max_rows = None if row_limit <= 0 else row_limit
            importer.test_control_value = control_tag if control_tag else None
            importer.matched_records = 0
            importer.unmatched_records = 0
            importer.processed_records = 0
            importer.cancel_requested = False

            self.active_importer = importer
            self._queue_status("Running import...")

            success = importer.run_import()

            if importer.cancel_requested:
                self.message_queue.put({'type': 'cancelled'})
            else:
                self.message_queue.put({
                    'type': 'done',
                    'success': success,
                    'matched': importer.matched_records,
                    'unmatched': importer.unmatched_records
                })

        except Exception as exc:
            self.message_queue.put({'type': 'error', 'message': str(exc)})
        finally:
            self.active_importer = None

    def _run_cleanup_thread(self, control_tag: str) -> None:
        try:
            importer = ExcelImporter()
            importer.test_control_value = control_tag
            success = importer.cleanup_test_records()
            self.message_queue.put({'type': 'cleanup_done', 'success': success})
        except Exception as exc:
            self.message_queue.put({'type': 'error', 'message': str(exc)})
        finally:
            self.active_importer = None

    def _queue_progress(self, message: str, percent: Optional[float]) -> None:
        self.message_queue.put({'type': 'progress', 'message': message, 'percent': percent})

    def _queue_status(self, message: str) -> None:
        self.message_queue.put({'type': 'status', 'message': message})

    def _process_queue(self) -> None:
        try:
            while True:
                item = self.message_queue.get_nowait()
                item_type = item.get('type')

                if item_type == 'progress':
                    self._append_log(item['message'])
                    percent = item.get('percent')
                    if percent is not None:
                        percent = max(0.0, min(100.0, float(percent)))
                        self.progress_var.set(percent)
                        self.progress_label.config(text=f"{percent:.1f}%")
                elif item_type == 'status':
                    self.status_var.set(item['message'])
                elif item_type == 'done':
                    self._handle_done(item)
                elif item_type == 'cleanup_done':
                    self._handle_cleanup_done(item)
                elif item_type == 'cancelled':
                    self._handle_cancelled()
                elif item_type == 'error':
                    self._handle_error(item['message'])

        except queue.Empty:
            pass

        self.after(100, self._process_queue)

    def _handle_done(self, item: dict) -> None:
        success = item.get('success', False)
        matched = item.get('matched', 0)
        unmatched = item.get('unmatched', 0)

        if success:
            self.status_var.set("Import completed successfully.")
            self._append_log("Import completed successfully.")
            self.progress_var.set(100.0)
            self.progress_label.config(text="100.0%")
            messagebox.showinfo(
                "Import Complete",
                f"Import finished. Matched: {matched}, Unmatched: {unmatched}."
            )
        else:
            if self.active_importer and self.active_importer.cancel_requested:
                self._handle_cancelled()
            else:
                self.status_var.set("Import failed. Check logs.")
                self._append_log("Import failed. Check logs for details.")
                messagebox.showerror("Import Failed", "The import did not complete successfully.")

        self._set_running_state(False)
        self.current_operation = None

    def _handle_cleanup_done(self, item: dict) -> None:
        success = item.get('success', False)
        if success:
            self.status_var.set("Cleanup completed.")
            self._append_log("Cleanup completed successfully.")
            messagebox.showinfo("Cleanup Complete", "Tagged records cleanup completed.")
        else:
            self.status_var.set("Cleanup failed.")
            self._append_log("Cleanup failed. Check logs for details.")
            messagebox.showerror("Cleanup Failed", "Cleanup did not complete successfully.")

        self._set_running_state(False)
        self.current_operation = None

    def _handle_cancelled(self) -> None:
        self.status_var.set("Import cancelled by user.")
        self._append_log("Import cancelled by user.")
        messagebox.showinfo("Import Cancelled", "The import was cancelled.")
        self._set_running_state(False)
        self.current_operation = None

    def _handle_error(self, message: str) -> None:
        self.status_var.set("Error encountered.")
        self._append_log(f"Error: {message}")
        messagebox.showerror("Error", message)
        self._set_running_state(False)
        self.current_operation = None

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _reset_progress(self) -> None:
        self.progress_var.set(0.0)
        self.progress_label.config(text="0.0%")
        self.status_var.set("Running...")
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _set_running_state(self, running: bool, allow_cancel: bool = True) -> None:
        if running:
            self.start_button.config(state=tk.DISABLED)
            self.cleanup_button.config(state=tk.DISABLED)
            if allow_cancel:
                self.cancel_button.config(state=tk.NORMAL)
            else:
                self.cancel_button.config(state=tk.DISABLED)
        else:
            self.start_button.config(state=tk.NORMAL)
            self.cleanup_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)

    def run(self) -> None:
        self.mainloop()


def main() -> None:
    app = ImportApp()
    app.run()


if __name__ == "__main__":
    main()

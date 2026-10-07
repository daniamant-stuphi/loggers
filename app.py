"""Test Lab Report Generator application.

A tkinter-based GUI for generating test lab reports with options to select
loggers and configure various parameters.
"""

import tkinter as tk
from tkinter import messagebox, ttk
import logging
import os
import threading
from tempfile import gettempdir

import numpy as np

import mem2txt
import report
from ftp_utils import fetch_file_via_ftp

# Constants
WINDOW_TITLE = "Select Options"
WINDOW_WIDTH = 500
WINDOW_HEIGHT = 300
APP_TITLE = "Test Lab Report Generator"
TITLE_FONT = ("Arial", 16, "bold")
MAIN_PADDING = {"padx": 20, "pady": 15}
FRAME_PADDING = {"padx": 10, "pady": 5}
BUTTON_WIDTH = 10
BUTTON_PADDING = 10

# Logger selection options
LOGGER_OPTIONS = {
    1: "Logger 4",
    2: "Logger 5",
    3: "Recover Old Data",
}


# Logger IP addresses
LOGGER_IPS = {
    # 1: "192.168.10.34",  # Logger 4
    # 2: "192.168.10.35",  # Logger 5
    1: "192.168.10.54",  # Logger 4
    2: "192.168.10.55",  # Logger 5
    3: "0.0.0.0"   # Recover Old Data
}

# Selecting this logger option reuses the last downloaded MEMDATA.MEM
RECOVER_OLD_DATA = 3

# Logger memory file and its text conversion, both kept in the temp directory
MEM_FILENAME = "MEMDATA.MEM"
MEM_PATH = os.path.join(gettempdir(), MEM_FILENAME)
TXT_PATH = os.path.join(gettempdir(), "MEMDATA.TXT")

# How often the progress dialog checks on the download/conversion thread
PROGRESS_POLL_MS = 100

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReportGeneratorApp:
    """Main application class for the Test Lab Report Generator GUI."""

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the application window and widgets.

        Args:
            root: The root tkinter window.
        """
        self.root = root
        self._setup_window()
        self._setup_variables()
        self._setup_ui()

    def _setup_window(self) -> None:
        """Configure the main window properties."""
        self.root.title(WINDOW_TITLE)
        self.root.resizable(False, False)
        logger.info("Window initialized: %s", WINDOW_TITLE)

    def _setup_variables(self) -> None:
        """Initialize tkinter variables for user selections."""
        self.logger_selection = tk.IntVar(value=3)  # Recover Old Data
        self.flashing_lights_enabled = tk.BooleanVar(value=False)
        self.battery_voltage_enabled = tk.BooleanVar(value=False)

    def _setup_ui(self) -> None:
        """Create and arrange all UI widgets."""
        # Main frame with padding
        main_frame = tk.Frame(self.root, **MAIN_PADDING)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title label
        self._create_title(main_frame)

        # Logger selection frame
        logger_frame = self._create_logger_selection(main_frame)
        logger_frame.grid(row=1, column=0, sticky="nw", padx=(0, 20))

        # Options frame (checkboxes)
        options_frame = self._create_options_frame(main_frame)
        options_frame.grid(row=1, column=1, sticky="w")

        # Report title frame
        title_entry_frame = self._create_report_title_frame(main_frame)
        title_entry_frame.grid(row=2, column=0, columnspan=2, pady=(20, 15), sticky="ew")

        # Buttons frame
        button_frame = self._create_button_frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2)

    def _create_title(self, parent: tk.Widget) -> tk.Label:
        """Create and return the title label.

        Args:
            parent: Parent widget to place the label in.

        Returns:
            The created title label widget.
        """
        title_label = tk.Label(
            parent, text=APP_TITLE, font=TITLE_FONT
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        return title_label

    def _create_logger_selection(self, parent: tk.Widget) -> tk.LabelFrame:
        """Create the logger selection radio button frame.

        Args:
            parent: Parent widget to place the frame in.

        Returns:
            The created logger selection frame.
        """
        logger_frame = tk.LabelFrame(parent, text="Logger Selection", **FRAME_PADDING)
        for value, label in LOGGER_OPTIONS.items():
            tk.Radiobutton(
                logger_frame,
                text=label,
                variable=self.logger_selection,
                value=value,
            ).pack(anchor="w", pady=2)
        return logger_frame

    def _create_options_frame(self, parent: tk.Widget) -> tk.Frame:
        """Create the checkbuttons frame for feature options.

        Args:
            parent: Parent widget to place the frame in.

        Returns:
            The created options frame.
        """
        options_frame = tk.Frame(parent)

        flashing_button = tk.Checkbutton(
            options_frame,
            text="Flashing Lights",
            variable=self.flashing_lights_enabled,
        )
        flashing_button.pack(anchor="w", pady=2)
        flashing_button.focus_set()  # Match focus dotted line from screenshot

        tk.Checkbutton(
            options_frame,
            text="Battery Voltage",
            variable=self.battery_voltage_enabled,
        ).pack(anchor="w", pady=2)

        return options_frame

    def _create_report_title_frame(self, parent: tk.Widget) -> tk.Frame:
        """Create the report title entry frame.

        Args:
            parent: Parent widget to place the frame in.

        Returns:
            The created report title frame.
        """
        title_entry_frame = tk.Frame(parent)
        tk.Label(title_entry_frame, text="Report Title  ").pack(side=tk.LEFT)
        self.title_entry = tk.Entry(title_entry_frame)
        self.title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        return title_entry_frame

    def _create_button_frame(self, parent: tk.Widget) -> tk.Frame:
        """Create the action buttons frame.

        Args:
            parent: Parent widget to place the frame in.

        Returns:
            The created button frame.
        """
        button_frame = tk.Frame(parent)

        tk.Button(
            button_frame,
            text="Cancel",
            width=BUTTON_WIDTH,
            command=self.on_cancel_clicked,
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)

        tk.Button(
            button_frame,
            text="OK",
            width=BUTTON_WIDTH,
            command=self.on_ok_clicked,
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)

        return button_frame

    def on_ok_clicked(self) -> None:
        """Handle the OK button click event."""
        logger_choice = self.logger_selection.get()
        report_title = self.title_entry.get()
        flashing_enabled = self.flashing_lights_enabled.get()
        battery_enabled = self.battery_voltage_enabled.get()

        logger.info(
            "Report generated - Logger: %s, Title: %s, Flashing: %s, Battery: %s",
            LOGGER_OPTIONS.get(logger_choice, "Unknown"),
            report_title if report_title else "No title",
            flashing_enabled,
            battery_enabled,
        )

        if not (flashing_enabled or battery_enabled):
            messagebox.showerror(
                "No Option Selected",
                "Select Flashing Lights and/or Battery Voltage to choose "
                "which values the report keeps.",
            )
            return

        if logger_choice == RECOVER_OLD_DATA and not os.path.exists(MEM_PATH):
            messagebox.showerror(
                "No Old Data",
                f"No previously downloaded {MEM_FILENAME} found at:\n{MEM_PATH}",
            )
            return

        summary = (
            f"Logger: {LOGGER_OPTIONS.get(logger_choice)}\n"
            f"Logger IP: {LOGGER_IPS.get(logger_choice)}\n"
            f"Title: {report_title if report_title else '(No title)'}\n"
            f"Flashing Lights: {'Yes' if flashing_enabled else 'No'}\n"
            f"Battery Voltage: {'Yes' if battery_enabled else 'No'}"
        )

        # Run the slow download/conversion/report in a worker thread so the progress
        # dialog stays responsive; the worker only sets attributes, and all
        # tkinter calls happen here on the main thread via polling.
        self._status = "Starting..."
        self._progress = None
        self._result = None
        self._show_progress_dialog()
        threading.Thread(
            target=self._generate_report,
            args=(logger_choice, report_title, flashing_enabled, battery_enabled),
            daemon=True,
        ).start()
        self.root.after(PROGRESS_POLL_MS, self._poll_worker, summary)

    def _show_progress_dialog(self) -> None:
        """Show a modal "in progress" dialog with a status line and busy bar."""
        self.progress_dialog = tk.Toplevel(self.root, **MAIN_PADDING)
        self.progress_dialog.title("Please Wait")
        self.progress_dialog.resizable(False, False)
        self.progress_dialog.transient(self.root)
        # Ignore the close button until the work finishes
        self.progress_dialog.protocol("WM_DELETE_WINDOW", lambda: None)

        self.progress_label = tk.Label(
            self.progress_dialog, text=self._status, width=45, anchor="w"
        )
        self.progress_label.pack()
        self.progress_detail = tk.Label(
            self.progress_dialog, text="", width=45, anchor="w"
        )
        self.progress_detail.pack(pady=(0, 10))
        self.progress_bar = ttk.Progressbar(
            self.progress_dialog, mode="indeterminate", length=300
        )
        self.progress_bar.pack()
        self.progress_bar.start()

        self.progress_dialog.grab_set()

    def _poll_worker(self, summary: str) -> None:
        """Update the progress dialog until the worker thread posts a result.

        Args:
            summary: Selected options, shown in the success message.
        """
        if self._result is None:
            self.progress_label.config(text=self._status)
            self._update_progress_bar()
            self.root.after(PROGRESS_POLL_MS, self._poll_worker, summary)
            return

        self.progress_bar.stop()
        self.progress_dialog.grab_release()
        self.progress_dialog.destroy()

        report_path, error = self._result
        if error is not None:
            messagebox.showerror(*error)
            return

        messagebox.showinfo(
            "Success",
            f"Report saved to:\n{report_path}\n\n{summary}",
        )

    def _update_progress_bar(self) -> None:
        """Show the download percentage, or a busy bar when it is unknown."""
        progress = self._progress
        if progress is not None and progress[1]:
            transferred, total = progress
            percent = min(100, transferred * 100 // total)
            if str(self.progress_bar["mode"]) != "determinate":
                self.progress_bar.stop()
                self.progress_bar.config(mode="determinate", maximum=100)
            self.progress_bar["value"] = percent
            self.progress_detail.config(
                text=f"{percent}%  ({transferred / 1e6:.1f} of {total / 1e6:.1f} MB)"
            )
            return

        if str(self.progress_bar["mode"]) != "indeterminate":
            self.progress_bar.config(mode="indeterminate")
            self.progress_bar.start()
        if progress is not None:
            # Server did not report the file size, so only bytes are known
            self.progress_detail.config(text=f"{progress[0] / 1e6:.1f} MB received")
        else:
            self.progress_detail.config(text="")

    def _record_progress(self, transferred: int, total: int | None) -> None:
        """FTP progress callback; runs in the worker thread."""
        self._progress = (transferred, total)

    def _generate_report(
        self,
        logger_choice: int,
        report_title: str,
        keep_peaks: bool,
        keep_minimums: bool,
    ) -> None:
        """Download MEMDATA.MEM (unless recovering old data), convert it to
        text, and write the Excel report to the current directory.

        Runs in a worker thread, so it must not touch tkinter. Progress is
        reported through self._status, and on completion self._result is set
        to (report_path, None) or (None, (error_title, error_message)).

        Args:
            logger_choice: Key into LOGGER_OPTIONS / LOGGER_IPS.
            report_title: Report title, also used for the file name.
            keep_peaks: Keep peak voltages (Flashing Lights).
            keep_minimums: Keep minimum voltages (Battery Voltage).
        """
        if logger_choice == RECOVER_OLD_DATA:
            logger.info("Using previously downloaded %s", MEM_PATH)
        else:
            ip_address = LOGGER_IPS[logger_choice]
            self._status = (
                f"Downloading {MEM_FILENAME} from "
                f"{LOGGER_OPTIONS[logger_choice]} ({ip_address})..."
            )
            downloaded = fetch_file_via_ftp(
                ip_address, MEM_FILENAME, on_progress=self._record_progress
            )
            self._progress = None
            if downloaded is None:
                self._result = (None, (
                    "Download Failed",
                    f"Could not download {MEM_FILENAME} from "
                    f"{LOGGER_OPTIONS[logger_choice]} ({ip_address}).",
                ))
                return

        self._status = f"Converting {MEM_FILENAME} to text..."
        try:
            info, channels, values = mem2txt.read_mem(MEM_PATH)
            mem2txt.write_txt(TXT_PATH, info, channels, values)
        except Exception as e:
            logger.exception("Failed to convert %s", MEM_PATH)
            self._result = (None, (
                "Conversion Failed", f"Could not convert {MEM_FILENAME}:\n{e}"
            ))
            return

        logger.info("Converted %d samples to %s", len(values), TXT_PATH)

        self._status = "Writing Excel report..."
        try:
            time_seconds = np.arange(len(values)) * info["interval"]
            report_path = report.build_report(
                time_seconds, values, report_title, keep_peaks, keep_minimums
            )
        except Exception as e:
            logger.exception("Failed to write report")
            self._result = (None, (
                "Report Failed",
                f"Could not write the Excel report:\n{e}\n\n"
                "If the file is open in Excel, close it and try again.",
            ))
            return

        logger.info("Report written to %s", report_path)
        self._result = (report_path, None)

    def on_cancel_clicked(self) -> None:
        """Handle the Cancel button click event."""
        logger.info("Application closed by user")
        self.root.destroy()


def main() -> None:
    """Main entry point for the application."""
    root = tk.Tk()
    app = ReportGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

"""Test Lab Report Generator application.

A tkinter-based GUI for generating test lab reports with options to select
loggers and configure various parameters.
"""

import tkinter as tk
from tkinter import messagebox
import logging

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
    1: "192.168.10.34",  # Logger 4
    2: "192.168.10.35",  # Logger 5
    3: "0.0.0.0"   # Recover Old Data
}

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
        self.logger_selection = tk.IntVar(value=2)
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

        messagebox.showinfo(
            "Success",
            f"Report generated successfully!\n\n"
            f"Logger: {LOGGER_OPTIONS.get(logger_choice)}\n"
            f"Logger IP: {LOGGER_IPS.get(logger_choice)}\n"
            f"Title: {report_title if report_title else '(No title)'}\n"
            f"Flashing Lights: {'Yes' if flashing_enabled else 'No'}\n"
            f"Battery Voltage: {'Yes' if battery_enabled else 'No'}",
        )

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

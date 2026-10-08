"""Build the Excel test report from parsed MEMDATA samples.

What each channel's column holds depends on the report options:

- Flashing Lights off: the raw samples. If there are more than MAX_RAW_ROWS
  of them, they are averaged over each REDUCE_WINDOW_SECONDS window instead.
- Flashing Lights on: the channels pulse (the voltage dips each time a light
  flashes), so each REDUCE_WINDOW_SECONDS window keeps its peak (resting
  voltage between flashes).
- Flashing Lights and Battery Voltage on: each window keeps its minimum
  (voltage under load) instead.

Usage:  python report.py [MEMDATA.TXT] [title] [raw|peak|min]
"""
import math
import os
import re
import sys
from tempfile import gettempdir

import numpy as np
import xlsxwriter

# Each output row summarises this many seconds of samples
REDUCE_WINDOW_SECONDS = 10

# Unprocessed data with more rows than this is averaged per window instead
MAX_RAW_ROWS = 50_000

# What each output row holds for a channel
MODE_RAW = "raw"
MODE_PEAK = "peak"
MODE_MIN = "min"

DATA_SHEET = "Data"
GRAPH_SHEET = "Graph"
DEFAULT_FILENAME = "report"

# Windows device names that cannot be used as a file name
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

# One distinct colour for each of the logger's up to 16 channels
CHANNEL_COLOURS = [
    "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
    "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
    "#393B79", "#637939", "#8C6D31", "#843C39", "#7B4173",
    "#000000",
]


def safe_filename(title: str) -> str:
    """Turn a report title into a safe .xlsx file name.

    Whitespace becomes '_', anything other than letters, digits, '_', '-'
    and '.' is dropped, and an empty or reserved result falls back to
    DEFAULT_FILENAME.
    """
    name = re.sub(r"\s+", "_", title.strip())
    name = re.sub(r"[^A-Za-z0-9_.-]", "", name)
    name = re.sub(r"_+", "_", name).strip("._-")
    if not name:
        name = DEFAULT_FILENAME
    if name.split(".")[0].upper() in RESERVED_NAMES:
        name = f"{name}_{DEFAULT_FILENAME}"
    return f"{name}.xlsx"


def report_mode(flashing_lights: bool, battery_voltage: bool) -> str:
    """Map the report options to MODE_RAW, MODE_PEAK or MODE_MIN.

    Battery Voltage only has an effect when Flashing Lights is selected.
    """
    if not flashing_lights:
        return MODE_RAW
    return MODE_MIN if battery_voltage else MODE_PEAK


def reduce_samples(
    time_seconds: np.ndarray,
    values: np.ndarray,
    mode: str,
    window_seconds: float = REDUCE_WINDOW_SECONDS,
) -> tuple[np.ndarray, np.ndarray]:
    """Reduce the samples to one row per window, as the mode requires.

    Args:
        time_seconds: Sample times in seconds.
        values: Channel values, one row per sample and one column per
            channel (the layout mem2txt.read_mem() returns).
        mode: MODE_RAW keeps the samples as they are (averaged per window
            if there are more than MAX_RAW_ROWS), MODE_PEAK keeps the
            maximum of each window and MODE_MIN the minimum.
        window_seconds: Length of each window.

    Returns:
        (time_hours, values): time_hours is the time of each row (the start
        of its window), and values has one row per output row and one
        column per channel.
    """
    times = np.asarray(time_seconds)
    values = np.asarray(values)
    if mode == MODE_RAW and len(times) <= MAX_RAW_ROWS:
        return times / 3600, values

    interval = times[1] - times[0] if len(times) > 1 else window_seconds
    samples_per_window = max(1, round(window_seconds / interval))
    starts = np.arange(0, len(times), samples_per_window)

    if mode == MODE_RAW:
        # Too dense, so average each window; a short final window still
        # gives a meaningful average
        counts = np.diff(np.append(starts, len(times)))
        reduced = np.add.reduceat(values, starts, axis=0) / counts[:, None]
        return times[starts] / 3600, reduced

    if len(starts) > 1 and len(times) - starts[-1] < samples_per_window:
        # A short final window may hold only part of a flash cycle, so its
        # peak/minimum is misleading; drop it.
        values = values[: starts[-1]]
        starts = starts[:-1]

    if mode == MODE_PEAK:
        reduced = np.maximum.reduceat(values, starts, axis=0)
    elif mode == MODE_MIN:
        reduced = np.minimum.reduceat(values, starts, axis=0)
    else:
        raise ValueError(f"Unknown report mode: {mode!r}")
    return times[starts] / 3600, reduced


def write_report(
    path: str,
    title: str,
    time_hours: np.ndarray,
    values: np.ndarray,
) -> None:
    """Write the data to a Data sheet and chart it on a Graph sheet."""
    with xlsxwriter.Workbook(path) as workbook:
        header_format = workbook.add_format({"bold": True, "bottom": 1})
        hours_format = workbook.add_format({"num_format": "0.0000"})
        volts_format = workbook.add_format({"num_format": "0.000"})

        sheet = workbook.add_worksheet(DATA_SHEET)
        channels = values.shape[1]
        headers = ["Time (h)"] + [
            f"Ch {channel + 1} (V)" for channel in range(channels)
        ]
        sheet.write_row(0, 0, headers, header_format)
        sheet.write_column(1, 0, time_hours.tolist(), hours_format)
        for channel in range(channels):
            sheet.write_column(
                1, channel + 1, values[:, channel].tolist(), volts_format
            )
        sheet.set_column(0, len(headers) - 1, 14)
        sheet.freeze_panes(1, 1)

        last_row = len(time_hours)
        chart = workbook.add_chart({"type": "scatter", "subtype": "straight"})
        for channel in range(channels):
            col = channel + 1
            chart.add_series({
                "name": [DATA_SHEET, 0, col],
                "categories": [DATA_SHEET, 1, 0, last_row, 0],
                "values": [DATA_SHEET, 1, col, last_row, col],
                "line": {
                    "color": CHANNEL_COLOURS[channel % len(CHANNEL_COLOURS)],
                    "width": 1,
                },
            })
        chart.set_title({"name": title or "Logger Data"})
        # Fixed axis formats (otherwise they inherit the cell formats), and a
        # voltage range around the data rather than from 0 V
        lowest = float(values.min())
        highest = float(values.max())
        chart.set_x_axis({
            "name": "Time (hours)",
            "min": 0,
            "max": max(1, math.ceil(float(time_hours[-1]))),
            "num_format": "0",
        })
        chart.set_y_axis({
            "name": "Voltage (V)",
            "min": math.floor(lowest * 2) / 2,
            "max": math.ceil(highest * 2) / 2,
            "num_format": "0.0",
        })
        chart.set_legend({"position": "right"})

        chartsheet = workbook.add_chartsheet(GRAPH_SHEET)
        chartsheet.set_chart(chart)
        chartsheet.activate()


def build_report(
    time_seconds: np.ndarray,
    values: np.ndarray,
    title: str,
    flashing_lights: bool,
    battery_voltage: bool,
) -> str:
    """Reduce the samples and write the report to the system temp directory,
    alongside the downloaded MEMDATA files.

    Args:
        flashing_lights: Keep each window's peak instead of the raw data.
        battery_voltage: With flashing_lights, keep each window's minimum
            instead of its peak. Ignored without flashing_lights.

    Returns:
        The absolute path of the written report.
    """
    time_hours, reduced = reduce_samples(
        time_seconds, values, report_mode(flashing_lights, battery_voltage)
    )
    path = os.path.join(gettempdir(), safe_filename(title))
    write_report(path, title, time_hours, reduced)
    return path


if __name__ == "__main__":
    from memdata_reader import read_memdata

    src = sys.argv[1] if len(sys.argv) > 1 else "MEMDATA.TXT"
    report_title = sys.argv[2] if len(sys.argv) > 2 else "Test Report"
    cli_mode = sys.argv[3] if len(sys.argv) > 3 else MODE_PEAK
    if cli_mode not in (MODE_RAW, MODE_PEAK, MODE_MIN):
        sys.exit(f"Mode must be {MODE_RAW}, {MODE_PEAK} or {MODE_MIN}")
    time_seconds, voltage_columns = read_memdata(src)
    path = build_report(
        np.array(time_seconds),
        np.array(voltage_columns).T,
        report_title,
        flashing_lights=cli_mode != MODE_RAW,
        battery_voltage=cli_mode == MODE_MIN,
    )
    print("Wrote", path)

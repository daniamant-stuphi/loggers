"""Build the Excel test report from parsed MEMDATA samples.

The logged channels pulse (the voltage dips each time a light flashes), so
the raw data is far too dense to chart. It is reduced to one row per
REDUCE_WINDOW_SECONDS window, keeping the peak (resting voltage between
flashes) and/or the minimum (voltage under load) of each channel.

Usage:  python report.py [MEMDATA.TXT] [title]
"""
import math
import os
import re
import sys

import numpy as np
import xlsxwriter

# Each output row summarises this many seconds of samples
REDUCE_WINDOW_SECONDS = 10

DATA_SHEET = "Data"
GRAPH_SHEET = "Graph"
DEFAULT_FILENAME = "report"

# Windows device names that cannot be used as a file name
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

# One colour per channel, so a channel's peak and minimum lines match
CHANNEL_COLOURS = [
    "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
    "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
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


def reduce_samples(
    time_seconds: np.ndarray,
    values: np.ndarray,
    keep_peaks: bool,
    keep_minimums: bool,
    window_seconds: float = REDUCE_WINDOW_SECONDS,
) -> tuple[np.ndarray, list[tuple[int, str, np.ndarray]]]:
    """Reduce the samples to one row per window.

    Args:
        time_seconds: Sample times in seconds.
        values: Channel values, one row per sample and one column per
            channel (the layout mem2txt.read_mem() returns).
        keep_peaks: Keep the maximum of each window.
        keep_minimums: Keep the minimum of each window.
        window_seconds: Length of each window.

    Returns:
        (time_hours, series): time_hours is the start of each window, and
        series is a list of (channel_index, kind, values) where kind is
        "peak" or "min".
    """
    times = np.asarray(time_seconds)
    values = np.asarray(values)
    interval = times[1] - times[0] if len(times) > 1 else window_seconds
    samples_per_window = max(1, round(window_seconds / interval))
    starts = np.arange(0, len(times), samples_per_window)
    if len(starts) > 1 and len(times) - starts[-1] < samples_per_window:
        # A short final window may hold only part of a flash cycle, so its
        # peak/minimum is misleading; drop it.
        values = values[: starts[-1]]
        starts = starts[:-1]

    peaks = np.maximum.reduceat(values, starts, axis=0) if keep_peaks else None
    minimums = np.minimum.reduceat(values, starts, axis=0) if keep_minimums else None

    series = []
    for channel in range(values.shape[1]):
        if peaks is not None:
            series.append((channel, "peak", peaks[:, channel]))
        if minimums is not None:
            series.append((channel, "min", minimums[:, channel]))
    return times[starts] / 3600, series


def write_report(
    path: str,
    title: str,
    time_hours: np.ndarray,
    series: list[tuple[int, str, np.ndarray]],
) -> None:
    """Write the reduced data to a Data sheet and chart it on a Graph sheet."""
    with xlsxwriter.Workbook(path) as workbook:
        header_format = workbook.add_format({"bold": True, "bottom": 1})
        hours_format = workbook.add_format({"num_format": "0.0000"})
        volts_format = workbook.add_format({"num_format": "0.000"})

        sheet = workbook.add_worksheet(DATA_SHEET)
        headers = ["Time (h)"] + [
            f"Ch {channel + 1} {kind} (V)" for channel, kind, _ in series
        ]
        sheet.write_row(0, 0, headers, header_format)
        sheet.write_column(1, 0, time_hours.tolist(), hours_format)
        for col, (_, _, values) in enumerate(series, start=1):
            sheet.write_column(1, col, values.tolist(), volts_format)
        sheet.set_column(0, len(headers) - 1, 14)
        sheet.freeze_panes(1, 1)

        last_row = len(time_hours)
        chart = workbook.add_chart({"type": "scatter", "subtype": "straight"})
        for col, (channel, kind, _) in enumerate(series, start=1):
            line = {
                "color": CHANNEL_COLOURS[channel % len(CHANNEL_COLOURS)],
                "width": 1,
            }
            if kind == "min":
                line["dash_type"] = "dash"
            chart.add_series({
                "name": [DATA_SHEET, 0, col],
                "categories": [DATA_SHEET, 1, 0, last_row, 0],
                "values": [DATA_SHEET, 1, col, last_row, col],
                "line": line,
            })
        chart.set_title({"name": title or "Logger Data"})
        # Fixed axis formats (otherwise they inherit the cell formats), and a
        # voltage range around the data rather than from 0 V
        lowest = min(float(values.min()) for _, _, values in series)
        highest = max(float(values.max()) for _, _, values in series)
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
    keep_peaks: bool,
    keep_minimums: bool,
) -> str:
    """Reduce the samples and write the report to the current directory.

    Returns:
        The absolute path of the written report.
    """
    time_hours, series = reduce_samples(
        time_seconds, values, keep_peaks, keep_minimums
    )
    path = os.path.abspath(safe_filename(title))
    write_report(path, title, time_hours, series)
    return path


if __name__ == "__main__":
    from memdata_reader import read_memdata

    src = sys.argv[1] if len(sys.argv) > 1 else "MEMDATA.TXT"
    report_title = sys.argv[2] if len(sys.argv) > 2 else "Test Report"
    time_seconds, voltage_columns = read_memdata(src)
    path = build_report(
        np.array(time_seconds), np.array(voltage_columns).T, report_title, True, True
    )
    print("Wrote", path)

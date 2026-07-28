"""Utilities for reading logger data from MEMDATA.TXT files."""

from __future__ import annotations

from pathlib import Path


def read_memdata(file_path: str | Path) -> tuple[list[float], list[list[float]]]:
    """Read numeric data columns from a MEMDATA.TXT export.

    The file contains several metadata/header rows before the actual sampled
    data. Parsing starts immediately after the row beginning with ``"Time"``.
    Data is returned in column format: a time column in seconds and a list of
    voltage columns.

    Args:
        file_path: Path to the MEMDATA.TXT file.

    Returns:
        A tuple containing:
        1. A list of time values in seconds.
        2. A list of voltage columns, where each inner list contains all values
           for one voltage channel.

    Raises:
        ValueError: If the data header cannot be found or a data row cannot be
            parsed as floats.
    """
    path = Path(file_path)
    time_seconds: list[float] = []
    voltage_columns: list[list[float]] = []
    data_section_started = False

    with path.open("r", encoding="utf-8") as memdata_file:
        for line_number, raw_line in enumerate(memdata_file, start=1):
            line = raw_line.strip()
            if not line:
                continue

            if not data_section_started:
                if line.startswith('"Time"'):
                    data_section_started = True
                continue

            try:
                row = [float(value.strip()) for value in line.split(",") if value.strip()]
            except ValueError as exc:
                raise ValueError(
                    f"Unable to parse numeric data on line {line_number}: {line}"
                ) from exc

            if not row:
                continue

            if len(row) < 2:
                raise ValueError(
                    f"Expected at least a time value and one data value on line {line_number}."
                )

            if not voltage_columns:
                # Ignore the trailing event column and keep only voltage data.
                voltage_columns = [[] for _ in range(len(row) - 2)]

            if len(row) != len(voltage_columns) + 2:
                raise ValueError(
                    f"Unexpected column count on line {line_number}: {len(row)} values found."
                )

            time_seconds.append(row[0])
            for index, value in enumerate(row[1:-1]):
                voltage_columns[index].append(value)

    if not data_section_started:
        raise ValueError(f'Could not find the "Time" header row in {path}.')

    return time_seconds, voltage_columns


def plot_memdata(
    time_seconds: list[float],
    voltage_columns: list[list[float]],
) -> None:
    """Plot MEMDATA voltage channels against time using matplotlib."""
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "matplotlib is required for plotting. Install it with 'pip install matplotlib'."
        ) from exc

    figure, axis = plt.subplots(figsize=(12, 6))

    for index, voltage_column in enumerate(voltage_columns, start=1):
        axis.plot(time_seconds, voltage_column, label=f"Channel {index}", linewidth=1)

    axis.set_title("MEMDATA Voltage Readings")
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Voltage (V)")
    axis.grid(True, alpha=0.3)
    axis.legend(loc="upper right", ncol=2)
    figure.tight_layout()
    plt.show()

if __name__ == "__main__":
    TEST_FILE_PATH = "MEMDATA.TXT"
    try:
        time_seconds, voltage_columns = read_memdata(TEST_FILE_PATH)
        print(f"Successfully read {len(time_seconds)} samples from {TEST_FILE_PATH}.")
        plot_memdata(time_seconds, voltage_columns)
    except Exception as e:
        print(f"Error reading MEMDATA.TXT: {e}")

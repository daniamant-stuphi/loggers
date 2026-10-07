# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Windows/Python tool ("Test Lab Report Generator") that downloads datalogger memory files over FTP, parses the sampled voltages, and is intended to produce an Excel report with a graph. The pipeline is **partly wired**: `app.py`'s `on_ok_clicked()` downloads `MEMDATA.MEM` over FTP and converts it to `MEMDATA.TXT` (both in `tempfile.gettempdir()`) with `mem2txt`, then passes the converted array (not the text file) to `report.py` to write the Excel report. This runs in a worker thread behind a progress dialog. `README.md` has a "What Still Needs To Be Implemented" list that describes the intended workflow.

## Commands

```powershell
uv sync                        # create/update .venv from uv.lock (Python 3.14 via .python-version)
uv run app.py                  # tkinter GUI
uv run ftp_utils.py            # live FTP download test (needs a logger on the LAN)
uv run memdata_reader.py       # parse + plot MEMDATA.TXT from the system temp dir
uv run mem2txt.py [MEMDATA.MEM] [output.txt]  # binary .MEM -> text export (default output memdata_converted.txt)
uv run report.py [MEMDATA.TXT] [title]        # text export -> <title>.xlsx in the cwd (peaks + minimums)
uv run pyinstaller app.spec    # build dist/app.exe (windowed, console=False)
```

Dependencies live in `pyproject.toml` (`uv add <pkg>`, or `uv add --dev <pkg>` for build tools such as pyinstaller); there is no `requirements.txt`. The project is not an installable package (`tool.uv.package = false`).

There are no automated tests, linter, or formatter configured.

## Architecture

Independent modules; the intended pipeline is GUI → FTP download → parse → Excel report:

- **`app.py`**: `ReportGeneratorApp` (tkinter). Logger choice is an `IntVar` key into two parallel dicts, `LOGGER_OPTIONS` (label) and `LOGGER_IPS` (IP). Keep them in sync when adding loggers. `Recover Old Data` (the default, key `RECOVER_OLD_DATA`) skips the download and reconverts the last downloaded `MEMDATA.MEM`; its `0.0.0.0` IP is unused.
- **`ftp_utils.py`**: `fetch_file_via_ftp(ip, filename)` does an anonymous login, `cwd("MEMORY")` on the logger, downloads into `tempfile.gettempdir()` via a `.part` file (so a failed download keeps the previous copy), and returns the local path. It returns `None` on any error instead of raising, and reports progress via `print`, so callers must check for `None`.
- **`memdata_reader.py`**: `read_memdata(path)` returns `(time_seconds, voltage_columns)` in column-major form. It raises `ValueError` on malformed data. `plot_memdata()` imports matplotlib lazily.

- **`report.py`**: `build_report()` reduces the samples to one row per `REDUCE_WINDOW_SECONDS` (10 s) window, keeping the per-channel peak (Flashing Lights) and/or minimum (Battery Voltage), and writes them with xlsxwriter to a `Data` sheet plus a `Graph` chartsheet. Time is in hours. The file is `safe_filename(title)` in the current working directory. A short final window is dropped because its peak or minimum would be misleading.

- **`mem2txt.py`**: standalone converter from the Hioki LR8400's binary `MEMDATA.MEM` to the same text format the logger exports as `MEMDATA.TXT`, so its output can be fed to `read_memdata()`. The header is a sequence of 0x200-byte blocks tagged `H…`, with fields stored as NUL-padded ASCII at fixed offsets. The `HW` block holds sample count, trigger date/time, interval and title, and there is one `HWC1` block per channel (mode, range, unit, scaling factor/offset). Sample data follows as big-endian int16, interleaved by sample, and is scaled by `raw * factor + offset`. The offsets were reverse-engineered from observed files, not a spec. It depends on numpy.

Because `memdata_reader.py`'s `__main__` reads from the temp dir, run `ftp_utils.py` first, or copy the sample file there.

## MEMDATA.TXT format

A CSV export from the logger (header says `MEMDATA.CSV`). It begins with about 10 quoted metadata rows (title comment such as `"Logger 4"`, trigger time, channel/mode/range/scaling rows). The data section starts after the row beginning `"Time"`, and each data row is:

```
time_s, ch1_V, ..., ch9_V, event,
```

Every row has a trailing comma, which the parser drops by skipping empty fields. The final event column is discarded. The column count is fixed by the first data row and validated on every row after it.

The checked-in sample `MEMDATA.TXT` is about 317k lines. Don't read it whole; use head/`Select-String`.

## Gotchas

- Keep `.gitignore` comments on their own lines. Git treats a `# comment` after a pattern as part of the pattern.
- When adding runtime dependencies (e.g. an Excel library), check `app.spec` (`hiddenimports`/`datas`) so the PyInstaller build includes them.

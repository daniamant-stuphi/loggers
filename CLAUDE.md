# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Windows/Python tool ("Test Lab Report Generator") that downloads datalogger memory files over FTP, parses the sampled voltages, and is intended to produce an Excel report with a graph. The pieces exist but are **not yet wired together**: `app.py`'s `on_ok_clicked()` only shows the selected options in a message box and does not call the FTP or parser modules. `README.md` has a "What Still Needs To Be Implemented" list that describes the intended workflow.

## Commands

```powershell
uv sync                        # create/update .venv from uv.lock (Python 3.14 via .python-version)
uv run app.py                  # tkinter GUI
uv run ftp_utils.py            # live FTP download test (needs a logger on the LAN)
uv run memdata_reader.py       # parse + plot MEMDATA.TXT from the system temp dir
uv run mem2txt.py [MEMDATA.MEM] [output.txt]  # binary .MEM -> text export (default output memdata_converted.txt)
uv run pyinstaller app.spec    # build dist/app.exe (windowed, console=False)
```

Dependencies live in `pyproject.toml` (`uv add <pkg>`, or `uv add --dev <pkg>` for build tools such as pyinstaller); there is no `requirements.txt`. The project is not an installable package (`tool.uv.package = false`).

There are no automated tests, linter, or formatter configured.

## Architecture

Independent modules; the intended pipeline is GUI → FTP download → parse → Excel report:

- **`app.py`**: `ReportGeneratorApp` (tkinter). Logger choice is an `IntVar` key into two parallel dicts, `LOGGER_OPTIONS` (label) and `LOGGER_IPS` (IP). Keep them in sync when adding loggers. `Recover Old Data` maps to `0.0.0.0` as a placeholder; its behaviour is undefined.
- **`ftp_utils.py`**: `fetch_file_via_ftp(ip, filename)` does an anonymous login, `cwd("MEMORY")` on the logger, downloads into `tempfile.gettempdir()`, and returns the local path. It returns `None` on any error instead of raising, and reports progress via `print`, so callers must check for `None`.
- **`memdata_reader.py`**: `read_memdata(path)` returns `(time_seconds, voltage_columns)` in column-major form. It raises `ValueError` on malformed data. `plot_memdata()` imports matplotlib lazily.

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

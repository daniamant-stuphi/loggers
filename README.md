# Test Lab Report Generator

This project is the start of a Windows/Python utility for downloading datalogger
memory files over FTP, reading the sampled data, and eventually producing an
Excel report with a graph.

At the moment the project is partly wired together. The GUI exists, the FTP
download helper exists, and the `MEMDATA.TXT` parser/plotter exists, but the GUI
does not yet run the full download-to-report workflow.

## Current Workflow

The current application entry point is `app.py`.

Running it opens a small tkinter window called **Test Lab Report Generator**. The
window lets the user:

- choose one of the configured logger options:
  - `Logger 4`, mapped to `192.168.10.34`
  - `Logger 5`, mapped to `192.168.10.35`
  - `Recover Old Data`, mapped to `0.0.0.0`
- tick report options for `Flashing Lights` and `Battery Voltage`
- enter a report title
- click `OK` or `Cancel`

Clicking `OK` currently logs the selected options and shows a success message
containing the selected logger, IP address, report title, and checkbox states.
It does not yet download data, parse data, or create an Excel file.

## Project Files

### `app.py`

This is the GUI application.

It defines:

- window title, size, button, and padding constants
- the available logger names in `LOGGER_OPTIONS`
- the configured logger IP addresses in `LOGGER_IPS`
- the `ReportGeneratorApp` tkinter class
- the `main()` function used when running the file directly

The GUI is split into small helper methods that create each section of the
window: title, logger radio buttons, option checkboxes, report title entry, and
OK/Cancel buttons.

The important current limitation is that `on_ok_clicked()` only reads the form
values and displays them. It does not yet call `ftp_utils.fetch_file_via_ftp()`
or `memdata_reader.read_memdata()`.

### `ftp_utils.py`

This file contains the FTP download helper.

`fetch_file_via_ftp(ip_address, remote_filename)`:

- connects to the given FTP server using port 21
- attempts a standard FTP login
- changes into the remote `MEMORY` directory
- tries to get the remote file size for progress reporting
- downloads the requested file with `retrbinary`
- saves the file into the user's temporary directory
- returns the local downloaded file path on success
- returns `None` if an FTP or unexpected error occurs

`create_progress_callback()` builds the callback used by `retrbinary`. It writes
downloaded chunks to disk and prints progress either as a percentage or as bytes
transferred if the FTP server does not support file sizes.

The file also contains a direct test block that tries to download `MEMDATA.TXT`
from `192.168.10.34`.

### `memdata_reader.py`

This file contains the data reader and a simple plotting helper.

`read_memdata(file_path)`:

- opens a `MEMDATA.TXT` file
- skips metadata/header lines until it finds a line starting with `"Time"`
- parses the remaining data rows as comma-separated floats
- stores the first column as time in seconds
- stores the middle columns as voltage channels
- ignores the final event column
- validates that each data row has the expected number of columns
- returns `(time_seconds, voltage_columns)`

`plot_memdata(time_seconds, voltage_columns)`:

- imports `matplotlib`
- plots each voltage channel against time
- labels the chart and shows it interactively

When `memdata_reader.py` is run directly, it reads the top-level `MEMDATA.TXT`
file and displays a matplotlib graph.

### `requirements.txt`

The only listed runtime dependency is:

```text
matplotlib>=3.8,<4.0
```

The GUI uses Python's built-in `tkinter` module. FTP support uses Python's
built-in `ftplib` module.

### `app.spec`, `build/`, and `dist/`

`app.spec` is a PyInstaller configuration for packaging `app.py` as a Windows
GUI executable named `app`.

The `build/` and `dist/` folders appear to be generated PyInstaller output.
`dist/app.exe` is the built executable.

### `MEMDATA.TXT`

This is a sample or captured datalogger memory file used by `memdata_reader.py`
for local parsing and plotting.

### `test.xlsx`

This appears to be an example spreadsheet or target output file. The current
Python code does not yet write to it.

## How To Run The Current Code

Create and activate a Python environment, then install the dependency:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Run the GUI:

```powershell
python app.py
```

Run the current parser/plotter against the local `MEMDATA.TXT`:

```powershell
python memdata_reader.py
```

Run the FTP helper test:

```powershell
python ftp_utils.py
```

The FTP test requires a reachable logger at `192.168.10.34` with a
`MEMORY/MEMDATA.TXT` file available.

## What Still Needs To Be Implemented

- Wire the GUI `OK` button into the real workflow.
- Use the selected logger to download `MEMDATA.TXT` with `fetch_file_via_ftp()`.
- Define what `Recover Old Data` should do, such as selecting a local
  `MEMDATA.TXT` file instead of using FTP.
- Pass the downloaded or selected file into `read_memdata()`.
- Generate an Excel workbook from the parsed data.
- Add a graph to the Excel workbook instead of only showing a matplotlib plot.
- Decide which voltage channels correspond to the `Flashing Lights` and
  `Battery Voltage` checkboxes.
- Use the report title in the generated spreadsheet.
- Add user-facing error messages for FTP failures, missing files, and invalid
  `MEMDATA.TXT` contents.
- Add a save-location prompt or default output naming convention for the Excel
  report.
- Add automated tests for MEMDATA parsing, FTP error handling, and report
  generation.
- Add Excel-writing dependencies, such as `openpyxl` or `xlsxwriter`, once the
  report format is chosen.
- Update the PyInstaller build once all runtime dependencies and data files are
  known.

## Suggested Next Step

The next useful implementation step is to connect `app.py` to the existing FTP
and parser modules: when the user clicks `OK`, download or select `MEMDATA.TXT`,
parse it with `read_memdata()`, and report any errors in the GUI.

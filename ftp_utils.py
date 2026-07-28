import ftplib
import os
from tempfile import gettempdir

def create_progress_callback(
    local_file,
    total_bytes: int | None,
):
    """Create a callback that writes chunks and prints download progress."""
    transferred_bytes = 0
    last_percent_reported = -1

    def progress_callback(data: bytes) -> None:
        nonlocal transferred_bytes, last_percent_reported

        local_file.write(data)
        transferred_bytes += len(data)

        if total_bytes and total_bytes > 0:
            percent_complete = int((transferred_bytes / total_bytes) * 100)
            if percent_complete > 100:
                percent_complete = 100

            if percent_complete != last_percent_reported:
                print(
                    f"\rDownloading... {percent_complete}% "
                    f"({transferred_bytes}/{total_bytes} bytes)",
                    end="",
                    flush=True,
                )
                last_percent_reported = percent_complete
        else:
            print(f"\rDownloading... {transferred_bytes} bytes", end="", flush=True)

    return progress_callback

def fetch_file_via_ftp(ip_address: str, remote_filename: str) -> str | None:
    """
    Connects to an FTP server, downloads a specified file, and saves it 
    to the user's temporary directory with progress indication.

    Args:
        ip_address: The IP address or hostname of the FTP server.
        remote_filename: The full path/name of the file on the remote server.

    Returns:
        The absolute path to the downloaded file in the temp directory, 
        or None if an error occurred.
    """
    # Determine the local path in the user's temporary directory
    local_filepath = os.path.join(gettempdir(), remote_filename)

    try:
        print(f"Attempting to connect to FTP server at: {ip_address}")
        with ftplib.FTP() as ftp:
            # Connect to the server (assuming default port 21)
            ftp.connect(ip_address)
            
            # Attempt anonymous login first, which is common for public test servers
            try:
                ftp.login() # Tries to log in with default credentials or fails gracefully if not needed
            except ftplib.error_perm:
                print("Warning: Could not perform standard FTP login; proceeding without explicit login.")

            # Download the file using RETR command, passing our progress callback
            ftp.cwd("MEMORY")
            total_bytes = None
            try:
                total_bytes = ftp.size(remote_filename)
            except ftplib.all_errors:
                # Some FTP servers do not support SIZE, so fall back to bytes-only progress.
                total_bytes = None

            with open(local_filepath, 'wb') as local_file:
                progress_callback = create_progress_callback(local_file, total_bytes)
                ftp.retrbinary(
                    f'RETR {remote_filename}',
                    progress_callback,
                    blocksize=8192,
                )

        print("\nSuccessfully downloaded file.")
        return local_filepath

    except ftplib.all_errors as e:
        print(f"\nFTP Error occurred while connecting or downloading: {e}")
        return None
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        return None

if __name__ == '__main__':
    # --- Example Usage (Requires a running FTP server for testing) ---
    # NOTE: Replace with actual credentials/server details for real use.
    TEST_IP = "192.168.10.34" # A public test FTP server
    TEST_FILE = "MEMDATA.TXT"   # A file known to exist on the test server

    print("--- Running FTP Test Example ---")
    downloaded_path = fetch_file_via_ftp(TEST_IP, TEST_FILE)
    
    if downloaded_path:
        print("\nTest successful. File path:", downloaded_path)
    else:
        print("\nTest failed or no file was downloaded.")

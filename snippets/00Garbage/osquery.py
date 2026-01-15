# Filepath: snippets/unSigned/osquery.py
#!/usr/bin/env python3
import platform
import subprocess
import sys
import os
import requests
from logzero import logger, logfile
from datetime import datetime

def initialize_logging():
    """Initialize logging with a timestamped log file."""
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"osquery_install_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logfile(log_file)
    logger.info("Initialized logging. Log file: %s", log_file)

def download_osquery(url, destination):
    """Download osquery installer from the specified URL."""
    try:
        logger.info("Downloading osquery from %s", url)
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info("Downloaded osquery to %s", destination)
    except Exception as e:
        logger.error("Failed to download osquery: %s", e)
        sys.exit(1)

def install_osquery_windows(installer_path):
    """Install osquery on Windows silently."""
    try:
        logger.info("Starting silent osquery installation on Windows.")
        result = subprocess.run(["msiexec", "/i", installer_path, "/qn", "/norestart"], check=True)
        logger.info("Osquery installed successfully on Windows. Exit code: %s", result.returncode)
    except subprocess.CalledProcessError as e:
        logger.error("Failed to install osquery on Windows: %s", e)
        sys.exit(1)

def install_osquery_macos(installer_path):
    """Install osquery on macOS silently."""
    try:
        logger.info("Starting silent osquery installation on macOS.")
        result = subprocess.run(["installer", "-pkg", installer_path, "-target", "/"], check=True)
        logger.info("Osquery installed successfully on macOS. Exit code: %s", result.returncode)
    except subprocess.CalledProcessError as e:
        logger.error("Failed to install osquery on macOS: %s", e)
        sys.exit(1)

def install_osquery_linux(archive_path):
    """Install osquery on Linux silently."""
    try:
        logger.info("Starting osquery installation on Linux.")
        subprocess.run(["tar", "-xzf", archive_path, "-C", "/usr/local/"], check=True)
        logger.info("Extracted osquery archive.")
        subprocess.run(["ln", "-sf", "/usr/local/osquery/bin/osqueryd", "/usr/bin/osqueryd"], check=True)
        subprocess.run(["ln", "-sf", "/usr/local/osquery/bin/osqueryi", "/usr/bin/osqueryi"], check=True)
        logger.info("Osquery installed successfully on Linux.")
    except subprocess.CalledProcessError as e:
        logger.error("Failed to install osquery on Linux: %s", e)
        sys.exit(1)

def main():
    """Main function to download and install osquery based on the OS."""
    initialize_logging()
    system = platform.system()
    logger.info("Detected operating system: %s", system)

    download_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_dir, exist_ok=True)

    if system == "Windows":
        url = "https://pkg.osquery.io/windows/osquery-5.14.1.msi"
        installer_path = os.path.join(download_dir, "osquery-5.14.1.msi")
        download_osquery(url, installer_path)
        install_osquery_windows(installer_path)
    elif system == "Darwin":
        url = "https://pkg.osquery.io/darwin/osquery-5.14.1.pkg"
        installer_path = os.path.join(download_dir, "osquery-5.14.1.pkg")
        download_osquery(url, installer_path)
        install_osquery_macos(installer_path)
    elif system == "Linux":
        url = "https://pkg.osquery.io/linux/osquery-5.14.1_1.linux_x86_64.tar.gz"
        archive_path = os.path.join(download_dir, "osquery-5.14.1_1.linux_x86_64.tar.gz")
        download_osquery(url, archive_path)
        install_osquery_linux(archive_path)
    else:
        logger.error("Unsupported operating system: %s", system)
        sys.exit(1)

    logger.info("Osquery installation process completed.")

if __name__ == "__main__":
    main()

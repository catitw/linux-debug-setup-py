import requests
from typing import Tuple
import hashlib
from tqdm import tqdm
import os
import platform


def download_file(url: str, save_path: str, desc: str) -> None:
    """
    Download a file from the given URL and save it to the specified path with
    a progress bar.

    Automatically creates parent directories if they do not exist.

    Args:
        url (str): The URL of the file to download.
        save_path (str): The path where the file will be saved.
        desc (str): Description for the progress bar.
    """
    # Ensure the parent directory exists
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with requests.get(url, stream=True) as response:
        response.raise_for_status()  # Raise HTTPError for bad responses
        total_size = int(response.headers.get(
            "content-length", 0))  # Get total file size
        chunk_size = 8192  # 8 KB

        # Set up the progress bar
        with tqdm(total=total_size, unit="B", unit_scale=True, desc=desc) as pbar:
            with open(save_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # Filter out keep-alive chunks
                        file.write(chunk)
                        pbar.update(len(chunk))


def get_remote_file_info(url: str) -> Tuple[int, str]:
    """
    Get the file size and ETag (if available) from the remote server.

    Args:
        url (str): The URL of the file.

    Returns:
        tuple: File size in bytes and ETag (if provided),
        or None if unavailable.
    """
    with requests.head(url) as response:
        response.raise_for_status()
        file_size = int(response.headers.get("content-length", 0))
        etag = response.headers.get("etag", "").strip(
            '"')  # Strip quotes if present
        return file_size, etag


def get_sha256_from_url(url: str) -> dict:
    """
    Fetch the SHA256 checksum file and parse it.

    Args:
        url (str): The URL of the checksum file.

    Returns:
        dict: A mapping of filenames to their checksums.
    """
    response = requests.get(url)
    response.raise_for_status()
    checksums = {}
    for line in response.text.splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            checksum, filename = parts
            checksums[filename.strip()] = checksum.strip()
    return checksums


def calculate_file_sha256(file_path: str) -> str:
    """
    Calculate the SHA256 checksum of a file.

    Args:
        file_path (str): The path of the file.

    Returns:
        str: The SHA256 checksum of the file.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_cpu_cores_minus_one():
    cores = os.cpu_count() or 1
    return max(cores - 1, 1)


def is_kvm_supported():
    """
    Check if the system supports KVM.
    Returns:
        bool: True if KVM is supported, False otherwise.
    """
    # Check if the platform is Linux
    if platform.system() != "Linux":
        return False

    # Check if /dev/kvm exists
    if not os.path.exists("/dev/kvm"):
        return False

    return True

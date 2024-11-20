import os

def get_state_dir() -> str:
    return os.path.abspath(".state")

def get_archlinux_iso_path() -> str:
    return f"{get_state_dir()}/archlinux-x86_64.iso"


def get_qemu_logfile_path() -> str:
    return f"{get_state_dir()}/qemu.log"


def get_rootfs_img_path() -> str:
    return os.path.abspath("./archlinux.img")


def get_linux_version() -> str:
    return "6.10"


def get_linux_src_dir() -> str:
    return os.path.abspath(f"./linux-{get_linux_version()}")


def get_linux_build_dir() -> str:
    return os.path.abspath(f"./linux-build-{get_linux_version()}")


def get_linux_config_script_path() -> str:
    return f"{get_linux_src_dir()}/scripts/config"


def get_linux_build_config_path() -> str:
    return f"{get_linux_build_dir()}/.config"

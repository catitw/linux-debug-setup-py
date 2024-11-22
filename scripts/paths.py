import os

from scripts.config import get_kernel_version


def get_state_dir() -> str:
    return os.path.abspath(".state")


def get_archlinux_iso_path() -> str:
    return f"{get_state_dir()}/archlinux-x86_64.iso"


def get_archlinux_iso_backup_path() -> str:
    return f"{get_state_dir()}/archlinux-x86_64-backup.iso"


def get_qemu_logfile_path() -> str:
    return f"{get_state_dir()}/qemu.log"


def get_rootfs_img_path() -> str:
    return os.path.abspath("./archlinux.img")


def get_linux_src_dir() -> str:
    return os.path.abspath(f"./linux-{get_kernel_version()}")


def get_linux_build_dir() -> str:
    return os.path.abspath(f"./linux-build-{get_kernel_version()}")


def get_linux_config_script_path() -> str:
    return f"{get_linux_src_dir()}/scripts/config"


def get_linux_build_config_path() -> str:
    return f"{get_linux_build_dir()}/.config"


def get_vscode_launch_path() -> str:
    return f"{get_linux_src_dir()}/.vscode/launch.json"


def get_run_qemu_sh_path() -> str:
    return os.path.abspath("run_qemu.sh")


def get_run_qemu_sh_debug_path() -> str:
    return os.path.abspath("run_qemu_debug.sh")


def get_vmlinux_path() -> str:
    return f"{get_linux_build_dir()}/vmlinux"


def get_bzimage_path() -> str:
    return f"{get_linux_build_dir()}/arch/x86_64/boot/bzImage"


def get_ovmf_vars_path() -> str:
    return f"{get_state_dir()}/OVMF_VARS.4m.fd"

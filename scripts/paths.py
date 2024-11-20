def get_state_dir() -> str:
    return ".state"


def get_archlinux_iso_path() -> str:
    return f"{get_state_dir()}/archlinux-x86_64.iso"


def get_rootfs_img_path() -> str:
    return "./archlinux.img"


def get_qemu_logfile_path() -> str:
    return f"{get_state_dir()}/qemu.log"

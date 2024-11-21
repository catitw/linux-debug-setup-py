import os
import sys
from dataclasses import dataclass
from enum import Enum

import toml

cached_rootfs_config = None
cached_qemu_config = None
cached_kernel_config = None


def parse_config() -> None:
    global cached_rootfs_config, cached_qemu_config, cached_kernel_config

    # Load and parse the TOML file
    with open(os.path.abspath("config.toml"), "r") as f:
        parsed_toml = toml.load(f)

    # Parse rootfs section
    rootfs_section = parsed_toml["rootfs"]

    # Validate 'format' field with fallback to qcow2 on error
    format_value = rootfs_section["format"]
    try:
        rootfs_format = QemuImgFormat(format_value)
    except ValueError:
        # Log warning and use default format qcow2
        print(
            f"Invalid format '{format_value}' config for qemu img found. Using default 'qcow2'.",
            file=sys.stderr,
        )
        rootfs_format = QemuImgFormat.QCOW2

    # Parse partitions and validate PartitionFormat
    partitions = []
    root_count = 0  # only one "/" mount point allowed
    for partition in rootfs_section["partitions"]:
        partition_format = PartitionFormat(partition["format"])  # Validate the format
        mount_point = partition["mount_point"]

        if not os.path.isabs(mount_point):
            raise ValueError(f"Mount point {mount_point} is not an absolute path.")

        if mount_point == "/":
            root_count += 1

        partition_config = PartitionFormatConfig(
            format=partition_format,
            size_gb=int(partition["size_gb"]),
            mount_point=mount_point,
        )
        partitions.append(partition_config)

    if root_count != 1:
        raise ValueError("There must be exactly one mount point with '/'.")

    cached_rootfs_config = RootfsConfig(
        archlinux_iso_url=rootfs_section["archlinux_iso_url"],
        archlinux_iso_sha256_url=rootfs_section["archlinux_iso_sha256_url"],
        format=rootfs_format,
        root_passwd=rootfs_section["root_passwd"],
        partitions=partitions,
    )

    # Parse qemu section
    qemu_section = parsed_toml["qemu"]

    # Parse `tcp_port_forward` and ensure it's a dictionary with integer keys and values
    tcp_port_forward_section = qemu_section.get("tcp_port_forward", {})
    if not isinstance(tcp_port_forward_section, dict):
        raise ValueError("`tcp_port_forward` must be a dictionary.")
    tcp_port_forward = {}
    for host_port, guest_port in tcp_port_forward_section.items():
        tcp_port_forward[int(host_port)] = int(guest_port)

    cached_qemu_config = QemuConfig(
        ovmf_code_fd_path=str(qemu_section["ovmf_code_fd_path"]),
        ovmf_vars_fd_path_copy_from=str(qemu_section["ovmf_vars_fd_path_copy_from"]),
        boot_mode=QemuBootMode(qemu_section["boot_mode"]),
        smp=int(qemu_section["smp"]),
        memory_gb=int(qemu_section["memory_gb"]),
        kvm_support=bool(qemu_section["kvm_support"]),
        tcp_port_forward=tcp_port_forward,
    )

    # Parse kernel section
    kernel_section = parsed_toml["kernel"]
    kernel_configure_overlay = {}

    for key, value in kernel_section["configure_overlay"].items():
        if value == "Y":
            kernel_configure_overlay[key] = KernelConfigOptYNM.Y
        elif value == "N":
            kernel_configure_overlay[key] = KernelConfigOptYNM.N
        elif value == "M":
            kernel_configure_overlay[key] = KernelConfigOptYNM.M
        elif isinstance(value, str):
            kernel_configure_overlay[key] = KernelConfigOptStr(value)
        elif isinstance(value, int):
            kernel_configure_overlay[key] = KernelConfigOptNum(value)

    cached_kernel_config = KernelConfig(
        version=kernel_section["version"],
        kernel_git_repo_url=kernel_section["kernel_git_repo_url"],
        configure_overlay=kernel_configure_overlay,
    )


class QemuImgFormat(Enum):
    RAW = "raw"
    QCOW2 = "qcow2"


class PartitionFormat(Enum):
    VFAT = "vfat"
    EXT4 = "ext4"


@dataclass
class PartitionFormatConfig:
    format: PartitionFormat
    size_gb: int
    mount_point: str


@dataclass
class RootfsConfig:
    archlinux_iso_url: str
    archlinux_iso_sha256_url: str
    format: QemuImgFormat
    root_passwd: str
    partitions: list[PartitionFormatConfig]


class KernelConfigOptYNM(Enum):
    Y = "Y"
    N = "N"
    M = "M"


@dataclass
class KernelConfigOptStr:
    val: str


@dataclass
class KernelConfigOptNum:
    val: int


KernelConfigOptValue = KernelConfigOptYNM | KernelConfigOptStr | KernelConfigOptNum


@dataclass
class KernelConfig:
    version: str
    kernel_git_repo_url: str
    configure_overlay: dict[str, KernelConfigOptValue]


class QemuBootMode(Enum):
    UEFI = "UEFI"
    BIOS = "BIOS"


@dataclass
class QemuConfig:
    ovmf_code_fd_path: str
    ovmf_vars_fd_path_copy_from: str
    boot_mode: QemuBootMode
    smp: int
    memory_gb: int
    kvm_support: bool
    tcp_port_forward: dict[int, int]  # host: guest


def get_archlinux_iso_url() -> str:
    return cached_rootfs_config.archlinux_iso_url  # type: ignore


def get_archlinux_iso_sha256_url() -> str:
    return cached_rootfs_config.archlinux_iso_sha256_url  # type: ignore


def get_rootfs_format() -> QemuImgFormat:
    return cached_rootfs_config.format  # type: ignore


def get_partitions() -> list[PartitionFormatConfig]:
    return cached_rootfs_config.partitions  # type: ignore


def get_rootfs_size_gb_ideal() -> int:
    return sum(partition.size_gb for partition in get_partitions())


def get_img_root_passwd() -> str:
    return cached_rootfs_config.root_passwd  # type: ignore


def get_kernel_version() -> str:
    return cached_kernel_config.version  # type: ignore


def get_kernel_git_repo() -> str:
    return cached_kernel_config.kernel_git_repo_url  # type: ignore


def get_kernel_config_opts() -> dict[str, KernelConfigOptValue]:
    return cached_kernel_config.configure_overlay  # type: ignore


def get_ovmf_code_fd_path() -> str:
    return cached_qemu_config.ovmf_code_fd_path  #  type: ignore


def get_ovmf_vars_fd_path_copy_from() -> str:
    return cached_qemu_config.ovmf_vars_fd_path_copy_from  # type: ignore


def get_qemu_boot_mode() -> QemuBootMode:
    return cached_qemu_config.boot_mode  # type: ignore


def get_qemu_smp() -> int:
    return cached_qemu_config.smp  # type: ignore


def get_qemu_memory_gb() -> int:
    return cached_qemu_config.memory_gb  # type: ignore


def get_qemu_kvm_support() -> bool:
    return cached_qemu_config.kvm_support  # type: ignore


def get_qemu_tcp_port_forward() -> dict[int, int]:
    return cached_qemu_config.tcp_port_forward  # type: ignore

import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Self, Tuple, Optional

import toml

cached_rootfs_config = None
cached_qemu_config = None
cached_kernel_config = None
cached_other_config = None


def parse_config() -> None:
    global cached_rootfs_config, cached_qemu_config, cached_kernel_config, cached_other_config

    # Load and parse the TOML file
    with open(os.path.abspath("config.toml"), "r") as f:
        parsed_toml = toml.load(f)

    cached_rootfs_config = RootfsConfig.parse(parsed_toml["rootfs"])

    cached_qemu_config = QemuConfig.parse(parsed_toml["qemu"])

    cached_kernel_config = KernelConfig.parse(parsed_toml["kernel"])

    cached_other_config = OtherConfig.parse(parsed_toml["other"])


class QemuImgFormat(Enum):
    RAW = "raw"
    QCOW2 = "qcow2"


class PartitionFormat(Enum):
    FAT = "fat"
    EXT4 = "ext4"

    def mkfs_cmd(self) -> str:
        match self:
            case PartitionFormat.FAT:
                return "mkfs.fat -F 32"
            case PartitionFormat.EXT4:
                return "mkfs.ext4"


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
    backup_iso_before_build: bool
    partitions_with_order: list[Tuple[PartitionFormatConfig, int]]

    @staticmethod
    def parse(conf_sec: dict[str, Any]) -> Self:
        # Validate 'format' field with fallback to qcow2 on error
        format_value = conf_sec["format"]
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
        efi_count = 0  # only one EFI partition allowed
        for partition in conf_sec["partitions"]:
            partition_format = PartitionFormat(
                partition["format"]
            )  # Validate the format
            mount_point = partition["mount_point"]

            if not os.path.isabs(mount_point):
                raise ValueError(f"Mount point {mount_point} is not an absolute path.")

            if partition_format == PartitionFormat.FAT:
                efi_count += 1

            if mount_point == "/":
                root_count += 1

            partition_config = PartitionFormatConfig(
                format=partition_format,
                size_gb=int(partition["size_gb"]),
                mount_point=mount_point,
            )
            partitions.append(partition_config)

        parts_order_list = [(c, i) for i, c in enumerate(partitions, start=1)]
        parts_order_list.sort(key=lambda x: len(x[0].mount_point))

        if efi_count != 1:
            raise ValueError("There must be exactly one EFI partition.")

        if root_count != 1:
            raise ValueError("There must be exactly one mount point with '/'.")

        return RootfsConfig(
            archlinux_iso_url=str(conf_sec["archlinux_iso_url"]),
            archlinux_iso_sha256_url=str(conf_sec["archlinux_iso_sha256_url"]),
            format=rootfs_format,
            root_passwd=str(conf_sec["root_passwd"]),
            backup_iso_before_build=bool(conf_sec["backup_iso_before_build"]),
            partitions_with_order=parts_order_list,
        )


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


class KernelVersionType(Enum):
    """Enum representing different kernel version specification types."""
    LATEST = "latest"
    BRANCH = "branch"
    TAG = "tag"
    COMMIT = "commit"


@dataclass
class KernelVersionConfig:
    """Configuration for kernel version specification."""
    type: KernelVersionType
    value: Optional[str] = None  # None for UNSPECIFIED, string value for others
    
    def get_git_ref(self) -> str:
        """Get the git reference string for fetching."""
        match self.type:
            case KernelVersionType.LATEST:
                return "HEAD"  # Default to latest
            case KernelVersionType.BRANCH:
                return self.value if self.value else "HEAD"
            case KernelVersionType.TAG:
                return f"v{self.value}" if self.value else "HEAD"
            case KernelVersionType.COMMIT:
                return self.value if self.value else "HEAD"
    
    def get_fetch_ref(self) -> str:
        """Get the reference for git fetch command."""
        match self.type:
            case KernelVersionType.LATEST:
                return "HEAD"
            case KernelVersionType.BRANCH:
                return self.value if self.value else "HEAD"
            case KernelVersionType.TAG:
                return self.value if self.value else "HEAD"
            case KernelVersionType.COMMIT:
                return self.value if self.value else "HEAD"


@dataclass
class KernelConfig:
    version_config: KernelVersionConfig
    kernel_git_repo_url: str
    build_with_rust: bool
    configure_overlay: dict[str, KernelConfigOptValue]

    @staticmethod
    def parse(conf_sec: dict[str, Any]) -> Self:
        kernel_configure_overlay = {}

        for key, value in conf_sec["configure_overlay"].items():
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

        # Parse version configuration
        version_config = KernelConfig._parse_version_config(conf_sec)

        return KernelConfig(
            version_config=version_config,
            kernel_git_repo_url=conf_sec["kernel_git_repo_url"],
            build_with_rust=conf_sec["build_with_rust"],
            configure_overlay=kernel_configure_overlay,
        )
    
    @staticmethod
    def _parse_version_config(conf_sec: dict[str, Any]) -> KernelVersionConfig:
        """Parse kernel version configuration from config section."""
        if "version_config" in conf_sec:
            version_conf = conf_sec["version_config"]
            if isinstance(version_conf, dict):
                version_type = KernelVersionType(version_conf["type"])
                version_value = version_conf.get("value")
                return KernelVersionConfig(type=version_type, value=version_value)
        
        # Default to latest if no version_config found
        return KernelVersionConfig(type=KernelVersionType.LATEST)


class QemuBootMode(Enum):
    UEFI = "UEFI"
    BIOS = "BIOS"


@dataclass
class QemuBootConfig:
    smp: int
    memory_gb: int


@dataclass
class QemuConfig:
    ovmf_code_fd_path: str
    ovmf_vars_fd_path_copy_from: str
    boot_mode: QemuBootMode
    kvm_support: bool
    tcp_port_forward: dict[int, int]  # host: guest
    build_rootfs: QemuBootConfig
    run_kernel: QemuBootConfig

    @staticmethod
    def parse(conf_sec: dict[str, Any]) -> Self:
        # Parse `tcp_port_forward` and ensure it's a dictionary with integer keys and values
        tcp_port_forward_section = conf_sec.get("tcp_port_forward", {})
        if not isinstance(tcp_port_forward_section, dict):
            raise ValueError("`tcp_port_forward` must be a dictionary.")
        tcp_port_forward = {}
        for host_port, guest_port in tcp_port_forward_section.items():
            tcp_port_forward[int(host_port)] = int(guest_port)

        qemu_build_rootfs_sec = conf_sec["build_rootfs"]
        qemu_build_rootfs = QemuBootConfig(
            smp=int(qemu_build_rootfs_sec["smp"]),
            memory_gb=int(qemu_build_rootfs_sec["memory_gb"]),
        )

        qemu_run_kernel_sec = conf_sec["run_kernel"]
        qemu_run_kernel = QemuBootConfig(
            smp=int(qemu_run_kernel_sec["smp"]),
            memory_gb=int(qemu_run_kernel_sec["memory_gb"]),
        )

        return QemuConfig(
            ovmf_code_fd_path=str(conf_sec["ovmf_code_fd_path"]),
            ovmf_vars_fd_path_copy_from=str(conf_sec["ovmf_vars_fd_path_copy_from"]),
            boot_mode=QemuBootMode(conf_sec["boot_mode"]),
            kvm_support=bool(conf_sec["kvm_support"]),
            tcp_port_forward=tcp_port_forward,
            build_rootfs=qemu_build_rootfs,
            run_kernel=qemu_run_kernel,
        )


@dataclass
class OtherConfig:
    build_with_ccache: bool

    @staticmethod
    def parse(conf: dict[str, Any]) -> Self:
        return OtherConfig(build_with_ccache=bool(conf["build_with_ccache"]))


def get_archlinux_iso_url() -> str:
    return cached_rootfs_config.archlinux_iso_url  # type: ignore


def get_archlinux_iso_sha256_url() -> str:
    return cached_rootfs_config.archlinux_iso_sha256_url  # type: ignore


def get_rootfs_format() -> QemuImgFormat:
    return cached_rootfs_config.format  # type: ignore


def get_backup_iso_before_build() -> bool:
    return cached_rootfs_config.backup_iso_before_build  # type: ignore


def get_partitions_with_order() -> list[Tuple[PartitionFormatConfig, int]]:
    return cached_rootfs_config.partitions_with_order  # type: ignore


def get_rootfs_size_gb_ideal() -> int:
    return sum(partition[0].size_gb for partition in get_partitions_with_order())


def get_img_root_passwd() -> str:
    return cached_rootfs_config.root_passwd  # type: ignore


def get_kernel_version_config() -> KernelVersionConfig:
    """Get the kernel version configuration object."""
    return cached_kernel_config.version_config  # type: ignore


def get_kernel_version() -> str:
    """Get kernel version string for backward compatibility.
    
    Returns the version value if available, otherwise returns 'latest'.
    """
    version_config = get_kernel_version_config()
    if version_config.value:
        return version_config.value
    return "latest"


def get_kernel_git_ref() -> str:
    """Get the git reference for kernel checkout."""
    return get_kernel_version_config().get_git_ref()


def get_kernel_fetch_ref() -> str:
    """Get the git reference for kernel fetch."""
    return get_kernel_version_config().get_fetch_ref()


def get_kernel_git_repo() -> str:
    return cached_kernel_config.kernel_git_repo_url  # type: ignore


def get_kernel_build_with_rust() -> bool:
    return cached_kernel_config.build_with_rust  # type: ignore


def set_kernel_build_with_rust(opt: bool) -> None:
    cached_kernel_config.build_with_rust = opt


def get_kernel_config_opts() -> dict[str, KernelConfigOptValue]:
    return cached_kernel_config.configure_overlay  # type: ignore


def get_ovmf_code_fd_path() -> str:
    return cached_qemu_config.ovmf_code_fd_path  #  type: ignore


def get_ovmf_vars_fd_path_copy_from() -> str:
    return cached_qemu_config.ovmf_vars_fd_path_copy_from  # type: ignore


def get_qemu_boot_mode() -> QemuBootMode:
    return cached_qemu_config.boot_mode  # type: ignore


def get_qemu_smp_when_build_rootfs() -> int:
    return cached_qemu_config.build_rootfs.smp  # type: ignore


def get_qemu_memory_gb_when_build_rootfs() -> int:
    return cached_qemu_config.build_rootfs.memory_gb  # type: ignore


def get_qemu_smp_when_run_kernel() -> int:
    return cached_qemu_config.run_kernel.smp  # type: ignore


def get_qemu_memory_gb_when_run_kernel() -> int:
    return cached_qemu_config.run_kernel.memory_gb  # type: ignore


def get_qemu_kvm_support() -> bool:
    return cached_qemu_config.kvm_support  # type: ignore


def get_qemu_tcp_port_forward() -> dict[int, int]:
    return cached_qemu_config.tcp_port_forward  # type: ignore


def get_build_with_ccache() -> bool:
    return cached_other_config.build_with_ccache

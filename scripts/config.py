
from dataclasses import dataclass
from enum import Enum


class QemuImgFormat(Enum):
    RAW = 1,
    QCOW2 = 2


def get_rootfs_format() -> QemuImgFormat:
    return QemuImgFormat.QCOW2


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


KernelConfigOptValue = KernelConfigOptYNM | KernelConfigOptStr | KernelConfigOptNum  # noqa: E501


def get_kernel_config_opts() -> dict[str, KernelConfigOptValue]:
    Y = KernelConfigOptYNM.Y
    N = KernelConfigOptYNM.N
    M = KernelConfigOptYNM.M

    # StrOpt = KernelConfigOptStr
    IntOpt = KernelConfigOptNum

    return {
        # disable optimize
        "CONFIG_CC_OPTIMIZE_FOR_PERFORMANCE": N,
        "CONFIG_CC_OPTIMIZE_FOR_SIZE": N,
        "CONFIG_OPTIMIZE_INLINING": N,
        "CONFIG_FUNCTION_TRACER": N,

        # disable optimize on X86
        "CONFIG_X86_GENERICARCH": N,

        # initramfs
        "CONFIG_BLK_DEV_INITRD": Y,
        "CONFIG_DEVTMPFS": Y,
        "CONFIG_DEVTMPFS_MOUNT": Y,


        "CONFIG_BLK_DEV_RAM": M,
        "CONFIG_BLK_DEV_RAM_COUNT": IntOpt(16),
        "CONFIG_BLK_DEV_RAM_SIZE": IntOpt(65536),
        "CONFIG_DEBUG_INFO": Y,
        "CONFIG_AS_HAS_NON_CONST_LEB128": Y,
        "CONFIG_DEBUG_INFO_NONE": N,
        "CONFIG_DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT": N,
        "CONFIG_DEBUG_INFO_DWARF4": N,
        "CONFIG_DEBUG_INFO_DWARF5": Y,
        "CONFIG_RANDOMIZE_BASE": N,
        "CONFIG_DEBUG_INFO_REDUCED": N,
        "CONFIG_DEBUG_INFO_COMPRESSED_NONE": Y,
        "CONFIG_DEBUG_INFO_COMPRESSED_ZLIB": Y,
        "CONFIG_DEBUG_INFO_COMPRESSED_ZSTD": N,
        "CONFIG_DEBUG_INFO_SPLIT": N,
        "CONFIG_GDB_SCRIPTS": Y,
        "CONFIG_FRAME_WARN": IntOpt(2048),
        "CONFIG_STRIP_ASM_SYMS": N,
        "CONFIG_READABLE_ASM": N,
        "CONFIG_HEADERS_INSTALL": N,
        "CONFIG_DEBUG_SECTION_MISMATCH": N,
        "CONFIG_SECTION_MISMATCH_WARN_ONLY": Y,
        "CONFIG_DEBUG_FORCE_WEAK_PER_CPU": N,
    }

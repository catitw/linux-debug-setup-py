
from enum import Enum


class QemuImgFormat(Enum):
    RAW = 1,
    QCOW2 = 2


def get_rootfs_format() -> QemuImgFormat:
    return QemuImgFormat.QCOW2

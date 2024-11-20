from scripts.args import parse_args, rebuild_rootfs
from scripts.rootfs import build_rootfs


def main() -> None:
    parse_args()

    if rebuild_rootfs():
        build_rootfs()

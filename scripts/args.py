import argparse


cached_args = None


def parse_args():
    global cached_args
    parser = argparse.ArgumentParser()

    parser.add_argument("--rebuild-rootfs", action="store_true", help="rebuild rootfs")

    parser.add_argument(
        "--force-skip-rootfs", action="store_true", help="force skip building rootfs"
    )

    parser.add_argument("--clean", action="store_true", help="clean linux")

    parser.add_argument("--distclean", action="store_true", help="clean all")

    cached_args = parser.parse_args()


def rebuild_rootfs_set() -> bool:
    return cached_args.rebuild_rootfs  # type: ignore


def force_skip_rootfs_set() -> bool:
    return cached_args.force_skip_rootfs  # type: ignore


def clean_linux_set() -> bool:
    return cached_args.clean  # type: ignore


def distclean_set() -> bool:
    return cached_args.distclean  # type: ignore

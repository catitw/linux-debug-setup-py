import argparse


cached_args = None


def parse_args():
    global cached_args
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--rebuild-rootfs",
        action="store_true",
        help="rebuild rootfs"
    )

    cached_args = parser.parse_args()


def rebuild_rootfs() -> bool:
    return cached_args.rebuild_rootfs  # type: ignore

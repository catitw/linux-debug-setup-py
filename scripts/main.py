import os

from scripts.args import (
    clean_linux_set,
    distclean_set,
    force_skip_rootfs_set,
    parse_args,
    rebuild_rootfs_set,
    skip_build_kernel_set,
)
from scripts.clean import clean_linux, distclean
from scripts.config import parse_config
from scripts.kernel import build_bzImage
from scripts.paths import get_rootfs_img_path
from scripts.rootfs import build_rootfs
from scripts.template import (
    gen_run_qemu_debug_sh,
    gen_run_qemu_sh,
    gen_vscode_launch_json,
)


def main() -> None:
    parse_args()
    parse_config()

    if distclean_set():
        distclean()
        return

    if clean_linux_set():
        clean_linux()
        return

    # build rootfs
    if rebuild_rootfs_set():
        build_rootfs()

    if not os.path.exists(get_rootfs_img_path()) and not force_skip_rootfs_set():
        print(
            "rootfs img not exists, building then. pass `--force-skip-rootfs` flag to avoid even if it not exists."
        )
        build_rootfs()
    else:
        print("skipping build rootfs img.")

    # build linux
    if not skip_build_kernel_set():
        build_bzImage()
    else:
        print("skipping build kernel")

    gen_vscode_launch_json()

    gen_run_qemu_sh()
    gen_run_qemu_debug_sh()

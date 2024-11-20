from scripts.args import clean_linux_set, distclean_set, parse_args, rebuild_rootfs_set
from scripts.kernel import build_bzImage
from scripts.rootfs import build_rootfs
from scripts.clean import clean_linux, distclean
from scripts.template import (
    gen_run_qemu_sh,
    gen_run_qemu_debug_sh,
    gen_vscode_launch_json,
)


def main() -> None:
    parse_args()

    if clean_linux_set():
        clean_linux()

    if distclean_set():
        distclean()

    if rebuild_rootfs_set():
        build_rootfs()

    build_bzImage()

    gen_vscode_launch_json()

    gen_run_qemu_sh()
    gen_run_qemu_debug_sh()

import os
import shutil
import sys

from scripts.kernel import linux_make_source
from scripts.paths import (
    get_linux_build_dir,
    get_linux_src_dir,
    get_ovmf_vars_path,
    get_rootfs_img_path,
    get_state_dir,
)
from scripts.state import KernelMachine, KernelState
from scripts.utils import remove_file_without_check


def clean_linux():
    if os.path.exists(get_linux_src_dir()):
        linux_make_source()
        KernelMachine.set_state(KernelState.SRC_CLONED)
    else:
        print("linux source directory not found! `make clean` skipped", file=sys.stderr)
        KernelMachine.clear_state()


def distclean():
    shutil.rmtree(get_state_dir(), ignore_errors=True)  # .state dir
    remove_file_without_check(get_rootfs_img_path())  # archlinux.img
    remove_file_without_check(get_ovmf_vars_path())  # OVMF_VARS.fd

    shutil.rmtree(get_linux_src_dir(), ignore_errors=True)  # linux src
    shutil.rmtree(get_linux_build_dir(), ignore_errors=True)  # linux build

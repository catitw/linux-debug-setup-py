import os
import shutil

from scripts.kernel import linux_make_source
from scripts.paths import (
    get_linux_build_dir,
    get_rootfs_img_path,
    get_state_dir,
    get_linux_src_dir,
)
from scripts.utils import remove_file_without_check


def clean_linux():
    if os.path.exists(get_linux_src_dir()):
        linux_make_source()


def distclean():
    shutil.rmtree(get_state_dir(), ignore_errors=True)  # .state dir
    remove_file_without_check(get_rootfs_img_path())  # archlinux.img

    shutil.rmtree(get_linux_src_dir(), ignore_errors=True)  # linux src
    shutil.rmtree(get_linux_build_dir(), ignore_errors=True)  # linux build

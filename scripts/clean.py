
from scripts.paths import get_rootfs_img_path, get_state_dir
import shutil

from scripts.utils import remove_file_without_check


def clean_linux():
    pass


def distclean():
    shutil.rmtree(get_state_dir(), ignore_errors=True)  # .state dir
    remove_file_without_check(get_rootfs_img_path())  # archlinux.img

import os
import shutil
import subprocess
import sys

import pexpect

from scripts.config import (
    PartitionFormat,
    QemuBootMode,
    QemuImgFormat,
    get_archlinux_iso_sha256_url,
    get_archlinux_iso_url,
    get_backup_iso_before_build,
    get_img_root_passwd,
    get_partitions_with_order,
    get_qemu_boot_mode,
    get_qemu_kvm_support,
    get_qemu_memory_gb_when_build_rootfs,
    get_qemu_smp_when_build_rootfs,
    get_rootfs_format,
    get_rootfs_size_gb_ideal,
)
from scripts.paths import (
    get_archlinux_iso_backup_path,
    get_archlinux_iso_path,
    get_rootfs_img_path,
)
from scripts.template import uefi_boot_mode_args
from scripts.utils import (
    calculate_file_sha256,
    download_file,
    get_sha256_from_url,
    mount_point_contains_efi,
)

SHELL_PROMPT_RE = ".*root.*@archiso.*~.*#"
CHANGE_ROOT_PROMPT_RE = "[.*root.*@archiso.*]"


def build_rootfs() -> None:
    ensure_iso_available(get_archlinux_iso_path())
    reprpare_rootfs_img()

    child = start_qemu()
    boot_to_console(child)

    pre_install(child)

    install_base_system(child)

    change_root(child)

    configure_system(child)

    shutdown(child)


def ensure_iso_available(save_path: str):
    iso_url = get_archlinux_iso_url()
    sha256_url = get_archlinux_iso_sha256_url()

    checksums = get_sha256_from_url(sha256_url)
    iso_filename = os.path.basename(save_path)

    if iso_filename not in checksums:
        raise Exception(f"Checksum for {iso_filename} not found in {sha256_url}")

    expected_checksum = checksums[iso_filename]

    # Check if the file exists and validate its checksum
    if os.path.exists(save_path):
        print(f"File {save_path} exists. Verifying checksum...")
        actual_checksum = calculate_file_sha256(save_path)
        if actual_checksum == expected_checksum:
            print("Checksum validation succeeded.")
            return
        else:
            print("Checksum validation failed. Redownloading file.")

    # Download the ISO file
    download_file(iso_url, save_path, "Downloading archlinux-x86_64.iso")

    # Verify the downloaded file
    print("Verifying downloaded file...")
    actual_checksum = calculate_file_sha256(save_path)
    if actual_checksum != expected_checksum:
        raise Exception(
            "Downloaded file checksum does not match. File may be corrupted."
        )

    print(f"File {save_path} is ready and verified.")


def reprpare_rootfs_img() -> None:
    """
    Prepare a root filesystem image file by ensuring it doesn't exist and
    creating a new image depands on the format required.

    Args:
        path (str): The path where the QCOW2 image should be created.
        size_GB (int): The desired size of the image in GB.
    """
    path = get_rootfs_img_path()
    size_gb = get_rootfs_size_gb_ideal() + 1

    # Step 1: Check if the file exists, if so, delete it
    if os.path.exists(path):
        print(f"File {path} already exists. Deleting it.")
        os.remove(path)

    def create_qcow2():
        print(f"Creating a new QCOW2 image at {path} with size {size_gb}GB.")
        subprocess.run(
            ["qemu-img", "create", "-f", "qcow2", path, f"{size_gb}G"], check=True
        )
        print(f"QCOW2 image {path} created successfully.")

    def create_raw():
        print(f"Creating a new RAW image at {path} with size {size_gb}GB.")
        subprocess.run(
            ["qemu-img", "create", "-f", "raw", path, f"{size_gb}G"], check=True
        )
        print(f"RAW image {path} created successfully.")

    # Step 2: Create a new image file of the specified size
    if get_rootfs_format() == QemuImgFormat.QCOW2:
        create_qcow2()
    else:
        create_raw()

    if get_backup_iso_before_build():
        shutil.copy(get_archlinux_iso_path(), get_archlinux_iso_backup_path())


def run_command(child, expect_prompt, command, timeout: int | None = -1):
    """Send a command to the child process and wait for the expected prompt."""
    child.expect(expect_prompt, timeout=timeout)
    child.sendline(command)


def unlimited_wait_to(child, prompt: str):
    child.expect(prompt, timeout=None)
    child.sendline("")


def start_qemu():
    """Start QEMU with the specified configuration."""
    # qemu-system-x86_64 \
    #   -cpu host \
    #   -accel kvm \
    #   -smp 2 \
    #   -m 4G \
    #   -drive file=./archlinux.img,format=qcow2 \
    #   -cdrom ./archlinux.iso \
    #   -boot order=d \
    #   -nographic

    img_format_str = (
        ",format=qcow2" if get_rootfs_format() == QemuImgFormat.QCOW2 else ",format=raw"
    )

    iso_path = (
        get_archlinux_iso_backup_path()
        if get_backup_iso_before_build()
        else get_archlinux_iso_path()
    )

    qemu_command = ["qemu-system-x86_64"]
    if get_qemu_kvm_support():
        qemu_command += [
            "-cpu host",
            "-accel kvm",
        ]
    qemu_command += [
        f"-smp {get_qemu_smp_when_build_rootfs()}",
        f"-m {get_qemu_memory_gb_when_build_rootfs()}G",
        f"-drive file={get_rootfs_img_path()}" + img_format_str,
        f"-cdrom {iso_path}",
        "-boot order=d",
        "-nographic",
    ]
    if get_qemu_boot_mode() == QemuBootMode.BIOS:
        pass
    else:
        qemu_command += uefi_boot_mode_args()

    child = pexpect.spawn(
        " ".join(qemu_command), encoding="utf-8", echo=False, use_poll=False
    )
    child.logfile_read = sys.stdout

    return child


def boot_to_console(child):
    """Boot Arch Linux to console."""

    # we are now in TUI mode
    if get_qemu_boot_mode() == QemuBootMode.BIOS:
        child.expect("Automatic boot in")
        child.send("\t")
        run_command(
            child,
            "initrd=/arch/boot/x86_64/initramfs-linux.img",
            " console=ttyS0,38400",
        )
    else:
        child.expect("Boot in.*s")
        child.send("e")
        child.expect("archisobasedir")
        child.send("console=ttyS0,38400 ")
        child.send("\n")

    # normal terminal now
    child.expect("Started.*OpenSSH Daemon", timeout=60)
    child.expect("Arch Linux")
    run_command(child, "login", "root")
    run_command(child, SHELL_PROMPT_RE, "")  # Wait for prompt


def pre_install(child):
    run_command(child, SHELL_PROMPT_RE, "systemctl stop reflector.service")

    # check UEFI
    # see: https://wiki.archlinux.org/title/Installation_guide#Verify_the_boot_mode
    run_command(child, SHELL_PROMPT_RE, "cat /sys/firmware/efi/fw_platform_size")

    run_command(child, SHELL_PROMPT_RE, "timedatectl")

    def partition_disk(child):
        FDISK_PROMPT_RE = "Command.*(m.*for.*help)"
        conf_order_list = get_partitions_with_order()

        run_command(child, SHELL_PROMPT_RE, "fdisk /dev/sda")

        run_command(child, FDISK_PROMPT_RE, "g")

        # alloc size
        def do_partition(i: int, s: int):
            run_command(child, FDISK_PROMPT_RE, "n")
            run_command(child, f"Partition number \\({i}-.*, default {i}\\):", "")
            run_command(child, "First sector \\(.*-.*, default .*\\):", "")
            run_command(child, "Last sector", f"+{s}G")

        conf_order_list.sort(key=lambda t: t[1])  # do partition order by the config
        for c, i in conf_order_list:
            do_partition(i, c.size_gb)

        # save partition
        run_command(child, FDISK_PROMPT_RE, "w")

    partition_disk(child)

    def format_disk(child):
        conf_order_list = get_partitions_with_order()

        def do_mkfs(n: int, c: PartitionFormat):
            run_command(child, SHELL_PROMPT_RE, f"{c.mkfs_cmd()} /dev/sda{n}")

        for c, i in conf_order_list:
            do_mkfs(i, c.format)

        # for check
        run_command(child, SHELL_PROMPT_RE, "fdisk -l /dev/sda")

    format_disk(child)

    def mount_disk(child):
        conf_order_list = get_partitions_with_order()

        for c, i in conf_order_list:
            if c.mount_point != "/":
                # do not touch "/mnt" dir in the iso file
                run_command(child, SHELL_PROMPT_RE, f"mkdir -p /mnt{c.mount_point}")

            run_command(
                child,
                SHELL_PROMPT_RE,
                f"mount /dev/sda{i} /mnt{c.mount_point}",
            )

    mount_disk(child)


def install_base_system(child):
    def setup_pacman_mirrorlist(child):
        run_command(
            child,
            SHELL_PROMPT_RE,
            "sed -i '1i Server = https://mirrors.nju.edu.cn/archlinux/$repo/os/$arch' /etc/pacman.d/mirrorlist",
        )

        run_command(child, SHELL_PROMPT_RE, "head -n 2 /etc/pacman.d/mirrorlist")
        run_command(child, SHELL_PROMPT_RE, "")

    setup_pacman_mirrorlist(child)

    def pacstrap(child):
        pacstrap_install_packages = [
            "base",
            "base-devel",
            "linux",
            "linux-headers",
            "linux-firmware",
            "dhcpcd",
            "iwd",
            "vim",
            "bash-completion",
            "xterm",  # we need the `resize` cmd
        ]

        run_command(
            child,
            SHELL_PROMPT_RE,
            "pacstrap -K /mnt " + " ".join(pacstrap_install_packages),
        )
        unlimited_wait_to(child, SHELL_PROMPT_RE)

    pacstrap(child)

    run_command(child, SHELL_PROMPT_RE, "genfstab -U /mnt >> /mnt/etc/fstab")


def change_root(child):
    run_command(child, SHELL_PROMPT_RE, "arch-chroot /mnt")


def configure_system(child):
    def sync_time(child):
        run_command(
            child,
            CHANGE_ROOT_PROMPT_RE,
            "ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime",
        )
        run_command(child, CHANGE_ROOT_PROMPT_RE, "hwclock --systohc")

    sync_time(child)

    def locale(child):
        run_command(
            child, CHANGE_ROOT_PROMPT_RE, "echo en_US.UTF-8 UTF-8 >> /etc/locale.gen"
        )
        run_command(
            child, CHANGE_ROOT_PROMPT_RE, "echo zh_CN.UTF-8 UTF-8 >> /etc/locale.gen"
        )
        run_command(child, CHANGE_ROOT_PROMPT_RE, "locale-gen")
        run_command(
            child, CHANGE_ROOT_PROMPT_RE, "echo LANG=en_US.UTF-8 > /etc/locale.conf"
        )

    locale(child)

    def network_conf(child):
        run_command(child, CHANGE_ROOT_PROMPT_RE, "echo arch-qemu > /etc/hostname")
        run_command(
            child,
            CHANGE_ROOT_PROMPT_RE,
            "echo -e '127.0.0.1  localhost\\n::1  localhost\\n127.0.1.1   arch-qemu' >> /etc/hosts",
        )

    network_conf(child)

    def set_root_password(child):
        root_passwd = get_img_root_passwd()

        run_command(child, CHANGE_ROOT_PROMPT_RE, "passwd root")
        run_command(child, "New password: ", root_passwd)
        run_command(child, "Retype new password: ", root_passwd)
        run_command(child, CHANGE_ROOT_PROMPT_RE, "")

    set_root_password(child)

    def setup_grub(child):
        run_command(
            child, CHANGE_ROOT_PROMPT_RE, "pacman -Sy --noconfirm grub efibootmgr"
        )
        run_command(
            child,
            CHANGE_ROOT_PROMPT_RE,
            f"grub-install --target=x86_64-efi --efi-directory={mount_point_contains_efi()} --bootloader-id=GRUB",
        )
        unlimited_wait_to(child, CHANGE_ROOT_PROMPT_RE)

        run_command(
            child, CHANGE_ROOT_PROMPT_RE, "grub-mkconfig -o /boot/grub/grub.cfg"
        )

    setup_grub(child)


def shutdown(child):
    """Exit the chroot and shutdown the system."""
    run_command(child, CHANGE_ROOT_PROMPT_RE, "exit")
    run_command(child, SHELL_PROMPT_RE, "umount -R  /mnt")
    run_command(child, SHELL_PROMPT_RE, "shutdown -h now")

    child.expect(pexpect.EOF)

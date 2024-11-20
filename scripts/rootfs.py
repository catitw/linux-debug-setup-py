import pexpect
from scripts.config import (
    PartitionFormat,
    QemuImgFormat,
    PartitionFormatConfig,
    get_archlinux_iso_sha256_url,
    get_archlinux_iso_url,
    get_img_root_passwd,
    get_partitions,
    get_rootfs_format,
    get_rootfs_size_gb_ideal,
)
from scripts.paths import get_archlinux_iso_path, get_rootfs_img_path
from scripts.utils import (
    get_cpu_cores_minus_one,
    get_sha256_from_url,
    calculate_file_sha256,
    download_file,
)
import os
import sys
import subprocess


SHELL_PROMPT_RE = ".*root.*@archiso.*~.*#"
CHANGE_ROOT_PROMPT_RE = "[.*root.*@archiso.*]"


def build_rootfs() -> None:
    ensure_iso_available(get_archlinux_iso_path())
    reprpare_rootfs_img()

    child = start_qemu()
    boot_to_console(child)
    format_disk_ext4(child)
    mount_disk(child)
    setup_pacman_mirrorlist(child)
    install_base_system(child)
    change_root(child)
    configure_system(child)
    set_root_password(child)
    setup_grub(child)
    shutdown_system(child)


def ensure_iso_available(save_path: str):
    iso_url = get_archlinux_iso_url()
    sha256_url = get_archlinux_iso_sha256_url()

    checksums = get_sha256_from_url(sha256_url)
    iso_filename = os.path.basename(save_path)

    if iso_filename not in checksums:
        raise Exception(f"Checksum for {iso_filename} not found in { sha256_url}")

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
        subprocess.run(["qemu-img", "create", path, f"{size_gb}G"], check=True)
        print(f"RAW image {path} created successfully.")

    # Step 2: Create a new image file of the specified size
    if get_rootfs_format() == QemuImgFormat.QCOW2:
        create_qcow2()
    else:
        create_raw()


def run_command(child, expect_prompt, command, timeout: int | None = -1):
    """Send a command to the child process and wait for the expected prompt."""
    child.expect(expect_prompt, timeout=timeout)
    child.sendline(command)


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

    qemu_command = [
        "qemu-system-x86_64",
        "-cpu host",
        "-accel kvm",
        f"-smp {get_cpu_cores_minus_one()}",
        "-m 8G",
        f"-drive file={get_rootfs_img_path()}" + img_format_str,
        f"-cdrom {get_archlinux_iso_path()}",
        "-boot order=d",
        "-nographic",
    ]
    child = pexpect.spawn(" ".join(qemu_command), encoding="utf-8")
    child.logfile_read = sys.stdout

    return child


def boot_to_console(child):
    """Boot Arch Linux to console."""
    child.expect("Automatic boot in")
    child.send("\t")  # speical hack for tui mode

    run_command(
        child, "initrd=/arch/boot/x86_64/initramfs-linux.img", " console=ttyS0,38400"
    )

    child.expect("Started.*OpenSSH Daemon")
    child.expect("Arch Linux")
    run_command(child, "login", "root")
    run_command(child, SHELL_PROMPT_RE, "")  # Wait for prompt


def format_disk_ext4(child):
    """Partition and format the disk."""
    FDISK_PROMPT_RE = "Command.*(m.*for.*help)"
    partition_conf = get_partitions()

    run_command(child, SHELL_PROMPT_RE, "fdisk /dev/sda")

    run_command(child, FDISK_PROMPT_RE, "g")

    # alloc size
    def do_partition(i: int, s: int):
        run_command(child, FDISK_PROMPT_RE, "n")
        run_command(child, f"Partition number \\({i}-.*, default {i}\\):", "")
        run_command(child, "First sector \\(.*-.*, default .*\\):", "")
        run_command(child, "Last sector", f"+{s}G")

    for i, c in enumerate(partition_conf, start=1):
        do_partition(i, c.size_gb)

    # save partition
    run_command(child, FDISK_PROMPT_RE, "w")

    def do_mkfs(n: int, c: PartitionFormat):
        run_command(child, SHELL_PROMPT_RE, f"mkfs.{c.value} /dev/sda{n}")

    for i, c in enumerate(partition_conf, start=1):
        do_mkfs(i, c.format)

    # for check
    run_command(child, SHELL_PROMPT_RE, "fdisk -l /dev/sda")


def mount_disk(child):
    partition_conf = get_partitions()
    partition_conf.sort(key=lambda x: len(x.mount_point))  # make sure "/" mount first

    for i, c in enumerate(partition_conf, start=1):
        run_command(child, SHELL_PROMPT_RE, f"mkdir -p /mnt/{c.mount_point}")
        run_command(
            child,
            SHELL_PROMPT_RE,
            f"mount /dev/sda{i} /mnt/{c.mount_point}",
        )


def setup_pacman_mirrorlist(child):
    run_command(
        child,
        SHELL_PROMPT_RE,
        "sed -i '1i Server = https://mirrors.ustc.edu.cn/archlinux/$repo/os/$arch' /etc/pacman.d/mirrorlist",
    )
    run_command(child, SHELL_PROMPT_RE, "head -n 4 /etc/pacman.d/mirrorlist")


def install_base_system(child):
    """Install the base system and generate the fstab."""

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
    ]

    run_command(
        child, SHELL_PROMPT_RE, "pacstrap /mnt " + " ".join(pacstrap_install_packages)
    )
    run_command(
        child, SHELL_PROMPT_RE, "genfstab -U /mnt >> /mnt/etc/fstab", timeout=None
    )  # we dont know when the last cmd `pacstrap` end


def change_root(child):
    run_command(child, SHELL_PROMPT_RE, "arch-chroot /mnt")


def configure_system(child):
    """Configure timezone, locale, hostname, and initramfs."""
    run_command(
        child,
        CHANGE_ROOT_PROMPT_RE,
        "ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime",
    )
    run_command(child, CHANGE_ROOT_PROMPT_RE, "hwclock --systohc")

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

    run_command(child, CHANGE_ROOT_PROMPT_RE, "echo arch-qemu > /etc/hostname")
    run_command(
        child,
        CHANGE_ROOT_PROMPT_RE,
        "echo -e '127.0.0.1  localhost\\n::1  localhost\\n127.0.1.1   arch-qemu' >> /etc/hosts",
    )


def set_root_password(child):
    """Set the root password."""
    root_passwd = get_img_root_passwd()

    run_command(child, CHANGE_ROOT_PROMPT_RE, "passwd root")
    run_command(child, "New password: ", root_passwd)
    run_command(child, "Retype new password: ", root_passwd)
    run_command(child, CHANGE_ROOT_PROMPT_RE, "")


def setup_grub(child):
    run_command(child, CHANGE_ROOT_PROMPT_RE, "pacman -S grub efibootmgr")
    run_command(
        child,
        CHANGE_ROOT_PROMPT_RE,
        "grub-install --target=x86_64-efi --efi-directory=/efi --bootloader-id=GRUB",
    )
    run_command(child, CHANGE_ROOT_PROMPT_RE, "grub-mkconfig -o /boot/grub/grub.cfg")


def shutdown_system(child):
    """Exit the chroot and shutdown the system."""
    run_command(child, CHANGE_ROOT_PROMPT_RE, "exit")
    run_command(child, SHELL_PROMPT_RE, "umount -R  /mnt")
    run_command(child, SHELL_PROMPT_RE, "shutdown -h now")

    child.expect(pexpect.EOF)

import pexpect
from scripts.config import QemuImgFormat, get_rootfs_format
from scripts.paths import get_archlinux_iso_path,  get_rootfs_img_path
from scripts.utils import get_cpu_cores_minus_one, get_sha256_from_url, calculate_file_sha256, download_file
import os
import sys
import subprocess

ISO_DOWNLOAD_URL = (
    "https://mirrors.ustc.edu.cn/archlinux/iso/latest/archlinux-x86_64.iso"
)

SHA256SUMS_URL = "https://mirrors.ustc.edu.cn/archlinux/iso/latest/sha256sums.txt"

SHELL_PROMPT_RE = ".*root.*@archiso.*~.*#"
CHANGE_ROOT_PROMPT_RE = "[.*root.*@archiso.*]"


def build_rootfs() -> None:
    ensure_iso_available(get_archlinux_iso_path())
    reprpare_rootfs_img(get_rootfs_img_path(), 40)

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
    checksums = get_sha256_from_url(SHA256SUMS_URL)
    iso_filename = os.path.basename(save_path)

    if iso_filename not in checksums:
        raise Exception(f"Checksum for {iso_filename} not found in {
                        SHA256SUMS_URL}")

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
    download_file(ISO_DOWNLOAD_URL, save_path,
                  "Downloading archlinux-x86_64.iso")

    # Verify the downloaded file
    print("Verifying downloaded file...")
    actual_checksum = calculate_file_sha256(save_path)
    if actual_checksum != expected_checksum:
        raise Exception(
            "Downloaded file checksum does not match. File may be corrupted.")

    print(f"File {save_path} is ready and verified.")


def reprpare_rootfs_img(path: str, size_GB: int) -> None:
    """
    Prepare a root filesystem image file by ensuring it doesn't exist and
    creating a new image depands on the format required.

    Args:
        path (str): The path where the QCOW2 image should be created.
        size_GB (int): The desired size of the image in GB.
    """
    # Step 1: Check if the file exists, if so, delete it
    if os.path.exists(path):
        print(f"File {path} already exists. Deleting it.")
        os.remove(path)

    def create_qcow2():
        print(f"Creating a new QCOW2 image at {path} with size {size_GB}GB.")
        subprocess.run(
            ["qemu-img", "create", "-f", "qcow2", path, f"{size_GB}G"],
            check=True
        )
        print(f"QCOW2 image {path} created successfully.")

    def create_raw():
        print(f"Creating a new RAW image at {path} with size {size_GB}GB.")
        subprocess.run(
            ["qemu-img", "create", path, f"{size_GB}G"],
            check=True
        )
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
    qemu_command = [
        "qemu-system-x86_64",
        "-cpu host",
        "-accel kvm",
        f"-smp {get_cpu_cores_minus_one()}",
        "-m 8G",
        f"-drive file={get_rootfs_img_path()}" +  # NOTE: '+' instead of ','
        ",format=qcow2" if get_rootfs_format() == QemuImgFormat.QCOW2 else "",
        f"-cdrom {get_archlinux_iso_path()}",
        "-boot order=d",
        "-nographic"
    ]
    child = pexpect.spawn(" ".join(qemu_command), encoding='utf-8')
    child.logfile_read = sys.stdout

    return child


def boot_to_console(child):
    """Boot Arch Linux to console."""
    child.expect("Automatic boot in")
    child.send("\t")     # speical hack for tui mode

    run_command(child, "initrd=/arch/boot/x86_64/initramfs-linux.img",
                " console=ttyS0,38400")

    child.expect("Started.*OpenSSH Daemon")
    child.expect("Arch Linux")
    run_command(child, "login", "root")
    run_command(child, SHELL_PROMPT_RE, "")  # Wait for prompt


def format_disk_ext4(child):
    """Partition and format the disk."""
    FDISK_PROMPT_RE = "Command.*(m.*for.*help)"

    run_command(child, SHELL_PROMPT_RE, "fdisk /dev/sda")

    run_command(child, FDISK_PROMPT_RE, "g")

    # /dev/sda1: 4G
    run_command(child, FDISK_PROMPT_RE, "n")
    run_command(child, "Partition number \\(1-.*, default 1\\):", "")
    run_command(child, "First sector \\(.*-.*, default .*\\):", "")
    run_command(child, "Last sector", "+4G")  # mksure we have 4G at least

    # /dev/sda2: rest
    run_command(child, FDISK_PROMPT_RE, "n")
    run_command(child, "Partition number \\(2-.*, default 2\\):", "")
    run_command(child, "First sector \\(.*-.*, default .*\\):", "")
    run_command(child, "Last sector", "")

    # save partition
    run_command(child, FDISK_PROMPT_RE, "w")

    # for check
    run_command(child, SHELL_PROMPT_RE, "fdisk -l /dev/sda")

    # setup fs
    run_command(child, SHELL_PROMPT_RE, "mkfs.vfat /dev/sda1")
    run_command(child, SHELL_PROMPT_RE, "mkfs.ext4 /dev/sda2")


def mount_disk(child):
    run_command(child, SHELL_PROMPT_RE, "mount /dev/sda2 /mnt")
    run_command(child, SHELL_PROMPT_RE, "mkdir /mnt/efi")
    run_command(child, SHELL_PROMPT_RE, "mount /dev/sda1 /mnt/efi")


def setup_pacman_mirrorlist(child):
    run_command(child, SHELL_PROMPT_RE,
                "sed -i '1i Server = https://mirrors.ustc.edu.cn/archlinux/$repo/os/$arch' /etc/pacman.d/mirrorlist")
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
        "bash-completion"
    ]

    run_command(child, SHELL_PROMPT_RE, "pacstrap /mnt " +
                " ".join(pacstrap_install_packages))
    run_command(child, SHELL_PROMPT_RE, "genfstab -U /mnt >> /mnt/etc/fstab",
                timeout=None)  # we dont know when the last cmd `pacstrap` end


def change_root(child):
    run_command(child, SHELL_PROMPT_RE, "arch-chroot /mnt")


def configure_system(child):
    """Configure timezone, locale, hostname, and initramfs."""
    run_command(child, CHANGE_ROOT_PROMPT_RE,
                "ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime")
    run_command(child, CHANGE_ROOT_PROMPT_RE, "hwclock --systohc")

    run_command(child, CHANGE_ROOT_PROMPT_RE,
                "echo en_US.UTF-8 UTF-8 >> /etc/locale.gen")
    run_command(child, CHANGE_ROOT_PROMPT_RE,
                "echo zh_CN.UTF-8 UTF-8 >> /etc/locale.gen")
    run_command(child, CHANGE_ROOT_PROMPT_RE, "locale-gen")
    run_command(child, CHANGE_ROOT_PROMPT_RE,
                "echo LANG=en_US.UTF-8 > /etc/locale.conf")

    run_command(child, CHANGE_ROOT_PROMPT_RE, "echo arch-qemu > /etc/hostname")
    run_command(child, CHANGE_ROOT_PROMPT_RE,
                "echo -e '127.0.0.1  localhost\\n::1  localhost\\n127.0.1.1   arch-qemu' >> /etc/hosts")


def set_root_password(child):
    """Set the root password."""
    run_command(child, CHANGE_ROOT_PROMPT_RE, "passwd root")
    run_command(child, "New password: ", "1")
    run_command(child, "Retype new password: ", "1")
    run_command(child, CHANGE_ROOT_PROMPT_RE, "")


def setup_grub(child):
    run_command(child, CHANGE_ROOT_PROMPT_RE, "pacman -S grub efibootmgr")
    run_command(child, CHANGE_ROOT_PROMPT_RE,
                "grub-install --target=x86_64-efi --efi-directory=/efi --bootloader-id=GRUB")
    run_command(child, CHANGE_ROOT_PROMPT_RE,
                "grub-mkconfig -o /boot/grub/grub.cfg")


def shutdown_system(child):
    """Exit the chroot and shutdown the system."""
    run_command(child, CHANGE_ROOT_PROMPT_RE, "exit")
    run_command(child, SHELL_PROMPT_RE, "umount -R  /mnt")
    run_command(child, SHELL_PROMPT_RE, "shutdown -h now")

    child.expect(pexpect.EOF)

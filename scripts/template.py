import os
import shutil

from scripts.config import (
    QemuBootMode,
    QemuImgFormat,
    get_ovmf_code_fd_path,
    get_ovmf_vars_fd_path_copy_from,
    get_qemu_boot_mode,
    get_qemu_kvm_support,
    get_qemu_memory_gb_when_run_kernel,
    get_qemu_smp_when_run_kernel,
    get_qemu_tcp_port_forward,
    get_rootfs_format,
)
from scripts.paths import (
    get_bzimage_path,
    get_linux_src_dir,
    get_ovmf_vars_path,
    get_rootfs_img_path,
    get_run_qemu_sh_debug_path,
    get_run_qemu_sh_path,
    get_vmlinux_path,
    get_vscode_launch_path,
)
from scripts.utils import (
    dev_partition_contains_root,
    ensure_dir_exist,
    ensure_exectuable,
)


def gen_vscode_launch_json() -> None:
    template = """
{{
  // Use IntelliSense to learn about possible attributes.
  // Hover to view descriptions of existing attributes.
  // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
  "version": "0.2.0",
  "configurations": [
    {{
      "name": "(gdb) linux",
      "type": "cppdbg",
      "request": "launch",
      "program": "{vmlinux}",
      "miDebuggerServerAddress": "localhost:1234",
      "args": [],
      "stopAtEntry": true,
      "cwd": "{workspaceFolder}",
      "environment": [],
      "externalConsole": false,
      "MIMode": "gdb",
      "miDebuggerArgs": "-n",
      "targetArchitecture": "x64",
      "setupCommands": [
        {{
          "text": "set arch i386:x86-64:intel",
          "ignoreFailures": false
        }},
        {{
          "text": "dir .",
          "ignoreFailures": false
        }},
        {{
          "text": "add-auto-load-safe-path ./",
          "ignoreFailures": false
        }},
        {{
          "text": "-enable-pretty-printing",
          "ignoreFailures": true
        }}
      ]
    }}
  ]
}}
"""
    vscode_launch = get_vscode_launch_path()
    ensure_dir_exist(os.path.dirname(vscode_launch))
    with open(vscode_launch, "w", encoding="utf-8") as file:
        file.write(
            template.format(
                vmlinux=get_vmlinux_path(),
                workspaceFolder=get_linux_src_dir(),
            )
        )


QEMU_TEMPLATE_BASE = r"""
#!/bin/bash
qemu-system-x86_64 \
    -smp {smp} \
    -m {memory_gb}G \
    -drive file={rootFsPath},format={rootFsFormat} \
    -kernel {bzImagePath} \
    -append "root={rootPartition} rw console=ttyS0 nokaslr" \
""".lstrip("\n")

KVM_APPEND = r"""
    -cpu host \
    -accel kvm \
""".lstrip("\n")

PORT_FORWARD_APPEND = r"""
    -net nic \
    -net user,hostfwd=tcp::2222-:22 \
    -net user,hostfwd=tcp::18000-:8000 \
    -net user,hostfwd=tcp::18001-:8001 \
    -net user,hostfwd=tcp::18002-:8002 \
    -net user,hostfwd=tcp::18003-:8003 \
    -net user,hostfwd=tcp::18004-:8004 \
""".lstrip("\n")

UEFI_BOOT_APPEND = r"""
    -drive if=pflash,format=raw,readonly=on,file={ovmfCodePath} \
    -drive if=pflash,format=raw,file={ovmfVarsPath} \
""".lstrip("\n")

RUN_QEMU_END = """
    -nographic
""".lstrip("\n")

RUN_QEMU_DEBUG_END = r"""
    -nographic \
    -S -s
""".lstrip("\n")

# qemu-system-x86_64 \
#     -cpu host \
#     -accel kvm \
#     -smp 2 \
#     -m 4G \
#     -drive file=./archlinux.img,format=raw \
#     -kernel ./linux-build-6.10/arch/x86_64/boot/bzImage \
#     -append "root=/dev/sda2 rw console=ttyS0 nokaslr" \
#     -nographic


def uefi_boot_mode_args() -> list[str]:
    """
    helper function to start qemu when building rootfs
    """

    boot_mode = get_qemu_boot_mode()
    ovmf_vars_path = get_ovmf_vars_path()

    # copy OVMF_VARS
    if boot_mode == QemuBootMode.UEFI:
        shutil.copy(get_ovmf_vars_fd_path_copy_from(), ovmf_vars_path)

    return [
        "-drive if=pflash,format=raw,readonly=on,file={ovmfCodePath}".format(
            ovmfCodePath=get_ovmf_code_fd_path()
        ),
        "-drive if=pflash,format=raw,file={ovmfVarsPath}".format(
            ovmfVarsPath=get_ovmf_vars_path()
        ),
    ]


def build_common_section() -> str:
    format_str = "qcow2" if get_rootfs_format() == QemuImgFormat.QCOW2 else "raw"
    tcp_port_foward_conf = get_qemu_tcp_port_forward()
    boot_mode = get_qemu_boot_mode()
    ovmf_vars_path = get_ovmf_vars_path()

    base = QEMU_TEMPLATE_BASE.format(
        smp=get_qemu_smp_when_run_kernel(),
        memory_gb=get_qemu_memory_gb_when_run_kernel(),
        rootFsPath=get_rootfs_img_path(),
        rootFsFormat=format_str,
        bzImagePath=get_bzimage_path(),
        rootPartition=dev_partition_contains_root(),
    )
    kvm = KVM_APPEND if get_qemu_kvm_support() else ""

    # copy OVMF_VARS
    if boot_mode == QemuBootMode.UEFI:
        shutil.copy(get_ovmf_vars_fd_path_copy_from(), ovmf_vars_path)

    boot_mode = (
        ""
        if boot_mode == QemuBootMode.BIOS
        else UEFI_BOOT_APPEND.format(
            ovmfCodePath=get_ovmf_code_fd_path(), ovmfVarsPath=ovmf_vars_path
        )
    )

    # e.g.:
    # -net nic \
    # -net user,hostfwd=tcp::2222-:22 \
    # -net user,hostfwd=tcp::18000-:8000 \
    port_forward_str = (
        ""
        if len(tcp_port_foward_conf) == 0
        else "    -net nic \\"
        + "\n"
        + "\n".join(
            [
                f"    -net user,hostfwd=tcp::{host_port}-:{guest_port} \\"
                for host_port, guest_port in tcp_port_foward_conf.items()
            ]
        )
        + "\n"
    )

    return base + kvm + boot_mode + port_forward_str


def gen_run_qemu_sh() -> None:
    sh_path = get_run_qemu_sh_path()
    with open(sh_path, "w", encoding="utf-8") as file:
        file.write(build_common_section() + RUN_QEMU_END)

    ensure_exectuable(sh_path)


def gen_run_qemu_debug_sh() -> None:
    sh_path = get_run_qemu_sh_debug_path()
    with open(sh_path, "w", encoding="utf-8") as file:
        file.write(build_common_section() + RUN_QEMU_DEBUG_END)

    ensure_exectuable(sh_path)

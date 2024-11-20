from scripts.config import QemuImgFormat, get_rootfs_format
from scripts.paths import (
    get_bzimage_path,
    get_linux_src_dir,
    get_rootfs_img_path,
    get_run_qemu_sh_debug_path,
    get_run_qemu_sh_path,
    get_vmlinux_path,
    get_vscode_launch_path,
)
from scripts.utils import ensure_dir_exist, ensure_exectuable
import os


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
      "cwd": "${workspaceFolder}",
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
    -smp 1 \
    -m 4G \
    -drive file={rootFsPath},format={rootFsFormat} \
    -kernel {bzImagePath} \
    -append "root=/dev/sda2 rw console=ttyS0 nokaslr" \
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


def gen_run_qemu_sh() -> None:
    template = QEMU_TEMPLATE_BASE + KVM_APPEND + PORT_FORWARD_APPEND + RUN_QEMU_END
    format_str = "qcow2" if get_rootfs_format() == QemuImgFormat.QCOW2 else "raw"

    sh_path = get_run_qemu_sh_path()
    with open(sh_path, "w", encoding="utf-8") as file:
        file.write(
            template.format(
                rootFsPath=get_rootfs_img_path(),
                rootFsFormat=format_str,
                bzImagePath=get_bzimage_path(),
            )
        )

    ensure_exectuable(sh_path)


def gen_run_qemu_debug_sh() -> None:
    template = (
        QEMU_TEMPLATE_BASE + KVM_APPEND + PORT_FORWARD_APPEND + RUN_QEMU_DEBUG_END
    )
    format_str = "qcow2" if get_rootfs_format() == QemuImgFormat.QCOW2 else "raw"

    sh_path = get_run_qemu_sh_debug_path()
    with open(sh_path, "w", encoding="utf-8") as file:
        file.write(
            template.format(
                rootFsPath=get_rootfs_img_path(),
                rootFsFormat=format_str,
                bzImagePath=get_bzimage_path(),
            )
        )

    ensure_exectuable(sh_path)

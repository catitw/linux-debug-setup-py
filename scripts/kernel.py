import os
import shutil
import subprocess

from scripts.config import (
    KernelConfigOptNum,
    KernelConfigOptStr,
    KernelConfigOptValue,
    KernelConfigOptYNM,
    get_kernel_config_opts,
    get_kernel_git_repo,
    get_kernel_version,
)
from scripts.paths import (
    get_linux_build_config_path,
    get_linux_build_dir,
    get_linux_config_script_path,
    get_linux_src_dir,
)
from scripts.state import KernelMachine, KernelState
from scripts.utils import get_cpu_cores_minus_one


def build_bzImage() -> None:
    cur_state_when_begin = KernelMachine.get_state()

    match cur_state_when_begin:
        case KernelState.DEFAULT_NOT_INIT:
            print("build kernel start with `clone source`")
            prepare_source()
        case KernelState.SRC_CLONED:
            print("build kernel start with `configure source`")
            configure_source()
        case KernelState.SRC_CONFIGURED:
            print("build kernel start with `build source`")
            build_source()


def prepare_source() -> None:
    linux_src = get_linux_src_dir()

    # ensure the `git init` and `git remote add` atomic
    try:
        if not os.path.exists(linux_src):
            subprocess.run(["git", "init", linux_src], check=True)
            run_under_source_dir_checked(
                ["git", "remote", "add", "origin", get_kernel_git_repo()],
            )
    except Exception as e:
        shutil.rmtree(linux_src)
        raise e

    run_under_source_dir_checked(
        ["git", "fetch", "--depth", "1", "origin", f"v{get_kernel_version()}"],
    )

    run_under_source_dir_checked(
        ["git", "checkout", "FETCH_HEAD"],
    )

    KernelMachine.set_state(KernelState.SRC_CLONED)

    configure_source()


def apply_custom_config(opt_key: str, opt_value: KernelConfigOptValue):
    script_path = get_linux_config_script_path()
    config_path = get_linux_build_config_path()

    match opt_value:
        case KernelConfigOptYNM.Y:
            subprocess.run(
                [script_path, "--file", config_path, "--enable", opt_key], check=True
            )
        case KernelConfigOptYNM.N:
            subprocess.run(
                [script_path, "--file", config_path, "--disable", opt_key], check=True
            )
        case KernelConfigOptYNM.M:
            subprocess.run(
                [script_path, "--file", config_path, "--module", opt_key], check=True
            )
        case KernelConfigOptStr(val):
            subprocess.run(
                [script_path, "--file", config_path, "--set-str", opt_key, val],  # noqa: E501
                check=True,
            )
        case KernelConfigOptNum(val):
            subprocess.run(
                [script_path, "--file", config_path, "--set-val", opt_key, str(val)],
                check=True,
            )


def configure_source() -> None:
    linux_build = get_linux_build_dir()
    jobs = get_cpu_cores_minus_one()

    run_under_source_dir_checked(["make", f"O={linux_build}", f"-j{jobs}", "defconfig"])

    for opt_key, opt_value in get_kernel_config_opts().items():
        apply_custom_config(opt_key, opt_value)

    run_under_source_dir_checked(["make", f"O={linux_build}", f"-j{jobs}", "oldconfig"])

    KernelMachine.set_state(KernelState.SRC_CONFIGURED)

    build_source()


def build_source() -> None:
    linux_src = get_linux_src_dir()
    linux_build = get_linux_build_dir()
    jobs = get_cpu_cores_minus_one()

    env = os.environ.copy()
    env["KBUILD_CFLAGS"] = "-fno-inline"

    subprocess.run(
        [
            "bear",
            "--append",
            "--output",
            f"{get_linux_src_dir()}/compile_commands.json",
            "--",
            "make",
            f"O={linux_build}",
            f"-j{jobs}",
        ],
        env=env,
        cwd=linux_src,
        check=True,
    )


def linux_make_source() -> None:
    linux_build = get_linux_build_dir()
    jobs = get_cpu_cores_minus_one()

    run_under_source_dir_checked(["make", f"O={linux_build}", f"-j{jobs}", "clean"])


def run_under_source_dir_checked(cmds: list[str]) -> None:
    subprocess.run(cmds, cwd=get_linux_src_dir(), check=True)

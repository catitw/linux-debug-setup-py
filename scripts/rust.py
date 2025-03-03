import shutil

from scripts.config import KernelConfigOptYNM
from scripts.utils import get_cpu_cores_minus_one


def apply_rust_config() -> None:
    from scripts.kernel import apply_custom_config

    apply_custom_config("CONFIG_RUST", KernelConfigOptYNM.Y)
    apply_custom_config("CONFIG_RUST_DEBUG_ASSERTIONS", KernelConfigOptYNM.Y)
    apply_custom_config("CONFIG_RUST_OVERFLOW_CHECKS", KernelConfigOptYNM.Y)
    apply_custom_config("CONFIG_RUST_BUILD_ASSERT_ALLOW", KernelConfigOptYNM.Y)
    apply_custom_config("CONFIG_SAMPLES", KernelConfigOptYNM.Y)
    apply_custom_config("CONFIG_SAMPLES_RUST", KernelConfigOptYNM.Y)
    apply_custom_config("CONFIG_RUST_FW_LOADER_ABSTRACTIONS", KernelConfigOptYNM.Y)
    apply_custom_config("CONFIG_BLK_DEV_RUST_NULL", KernelConfigOptYNM.M)
    apply_custom_config("CONFIG_RUST_PHYLIB_ABSTRACTIONS", KernelConfigOptYNM.Y)
    apply_custom_config("CONFIG_AMCC_QT2025_PHY", KernelConfigOptYNM.Y)

    # TODO: set following options of examples if user not set.
    apply_custom_config("CONFIG_SAMPLE_AUXDISPLAY", KernelConfigOptYNM.N)
    apply_custom_config("CONFIG_SAMPLE_TRACE_EVENTS", KernelConfigOptYNM.N)
    apply_custom_config("CONFIG_SAMPLE_TRACE_CUSTOM_EVENTS", KernelConfigOptYNM.N)
    apply_custom_config("CONFIG_SAMPLE_TRACE_PRINTK", KernelConfigOptYNM.N)
    apply_custom_config("CONFIG_SAMPLE_TRACE_ARRAY", KernelConfigOptYNM.N)
    apply_custom_config("CONFIG_SAMPLE_KOBJECT", KernelConfigOptYNM.N)
    apply_custom_config("CONFIG_SAMPLE_KPROBES", KernelConfigOptYNM.N)
    apply_custom_config("CONFIG_SAMPLE_HW_BREAKPOINT", KernelConfigOptYNM.N)
    apply_custom_config("CONFIG_SAMPLE_KFIFO", KernelConfigOptYNM.N)
    apply_custom_config("CONFIG_SAMPLE_WATCHDOG", KernelConfigOptYNM.N)

    apply_custom_config("CONFIG_SAMPLE_RUST_MINIMAL", KernelConfigOptYNM.M)
    apply_custom_config("CONFIG_SAMPLE_RUST_PRINT", KernelConfigOptYNM.M)
    apply_custom_config("CONFIG_SAMPLE_RUST_HOSTPROGS", KernelConfigOptYNM.Y)


def gen_rust_project_json() -> None:
    from scripts.paths import get_linux_src_dir, get_linux_build_dir
    from scripts.kernel import run_under_source_dir_checked

    linux_build = get_linux_build_dir()
    jobs = get_cpu_cores_minus_one()

    run_under_source_dir_checked(["make", f"O={linux_build}", f"-j{jobs}", "LLVM=1", "rust-analyzer"])

    shutil.copy(f"{get_linux_build_dir()}/rust-project.json", f"{get_linux_src_dir()}/rust-project.json")

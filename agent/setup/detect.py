"""Hardware detection — best-effort and safe to run anywhere."""
from __future__ import annotations

import platform
import shutil
import subprocess

from core.models import HardwareProfile


def detect_hardware() -> HardwareProfile:
    import psutil
    cpu_cores = psutil.cpu_count(logical=False) or 1
    ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
    cpu_brand = platform.processor() or platform.machine()
    system = platform.system()
    ollama_installed = shutil.which("ollama") is not None
    ollama_version = None
    if ollama_installed:
        try:
            ollama_version = subprocess.check_output(
                ["ollama", "--version"], text=True, timeout=5
            ).strip()
        except Exception:
            ollama_version = None

    gpu_vendor = None
    gpu_name = None
    gpu_vram_gb = None
    cuda = False
    rocm = False
    mps = system == "Darwin" and platform.machine() == "arm64"
    unified = mps
    unified_gb = ram_gb if unified else None
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            text=True, timeout=5,
        )
        line = out.strip().splitlines()[0]
        name, vram = [p.strip() for p in line.split(",")]
        gpu_vendor = "NVIDIA"
        gpu_name = name
        gpu_vram_gb = float(vram) / 1024
        cuda = True
    except Exception:
        pass

    return HardwareProfile(
        cpu_cores=cpu_cores,
        cpu_brand=cpu_brand,
        ram_gb=ram_gb,
        gpu_vendor=gpu_vendor,
        gpu_name=gpu_name,
        gpu_vram_gb=gpu_vram_gb,
        unified_memory=unified,
        unified_memory_gb=unified_gb,
        has_npu=False,
        cuda_available=cuda,
        rocm_available=rocm,
        mps_available=mps,
        ollama_installed=ollama_installed,
        ollama_version=ollama_version,
    )

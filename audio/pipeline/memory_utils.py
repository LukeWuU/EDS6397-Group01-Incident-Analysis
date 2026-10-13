"""GPU / RAM cleanup helpers for long batch runs."""

from __future__ import annotations

import gc


def clear_gpu_memory() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    except ImportError:
        return

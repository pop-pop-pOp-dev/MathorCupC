from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pipeline.runner import run_full_pipeline

if __name__ == '__main__':
    run_full_pipeline(Path(__file__).resolve().parents[1])

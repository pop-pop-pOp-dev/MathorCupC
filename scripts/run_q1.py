from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from utils.config import load_project_config
from utils.io import make_run_dir
from utils.seed import set_seed
from pipeline.stage_01_data import run_stage_01_data
from pipeline.stage_02_latent import run_stage_02_latent

root = Path(__file__).resolve().parents[1]
config = load_project_config(root)
set_seed(config['seed'])
run_dir = make_run_dir(root, config['paths']['outputs_dir'])
df = run_stage_01_data(config, run_dir)
run_stage_02_latent(df, config, run_dir)

from __future__ import annotations

from pathlib import Path
from utils.config import load_project_config
from utils.io import make_run_dir
from utils.logging_utils import get_logger
from utils.seed import set_seed
from pipeline.stage_01_data import run_stage_01_data
from pipeline.stage_02_latent import run_stage_02_latent
from pipeline.stage_03_risk import run_stage_03_risk
from pipeline.stage_04_rules import run_stage_04_rules
from pipeline.stage_05_optimize import run_stage_05_optimize
from pipeline.stage_06_validate import run_stage_06_validate
from reporting.figures import plot_risk_distribution

logger = get_logger(__name__)


def run_full_pipeline(project_root: str | Path | None = None):
    project_root = Path(project_root or Path(__file__).resolve().parents[2])
    config = load_project_config(project_root)
    set_seed(config['seed'])
    run_dir = make_run_dir(project_root, config['paths']['outputs_dir'])
    logger.info('Running stage 01: data governance and features')
    df = run_stage_01_data(config, run_dir)
    logger.info('Running stage 02: latent state')
    df = run_stage_02_latent(df, config, run_dir)
    logger.info('Running stage 03: risk stratification')
    df = run_stage_03_risk(df, config, run_dir)
    logger.info('Running stage 04: rule extraction')
    run_stage_04_rules(df, config, run_dir)
    logger.info('Running stage 05: intervention optimization')
    plans = run_stage_05_optimize(df, config, run_dir)
    logger.info('Running stage 06: validation')
    run_stage_06_validate(df, plans, config, run_dir)
    if config['runtime'].get('plots', False):
        plot_risk_distribution(df, run_dir / 'risk' / 'continuous_risk_score.png')
    logger.info('Pipeline finished: %s', run_dir)
    return run_dir

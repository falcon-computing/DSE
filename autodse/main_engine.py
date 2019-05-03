"""
The main DSE flow that integrates all modules
"""

import argparse
import json
import os

from autodse.config import check_config
from autodse.logger import get_logger
from autodse.database import RedisDatabase
from autodse.dsproc.dsproc import compile_design_space, partition
from autodse.evaluator.analyzer import MerlinAnalyzer
from autodse.evaluator.evaluator import BackupMode, EvalMode, MerlinEvaluator
from autodse.evaluator.scheduler import PythonSubprocessScheduler

ARG_PARSER = argparse.ArgumentParser(description='Automatic Design Space Exploration')
ARG_PARSER.add_argument('--src-dir', action='store', help='Merlin project directory')
ARG_PARSER.add_argument('--work-dir', action='store', default='.', help='DSE working directory')
ARG_PARSER.add_argument('--config', action='store', help='path to the configure JSON file')

LOG = get_logger('Main')


def main() -> None:
    """The main function of the DSE flow"""
    args = ARG_PARSER.parse_args()

    # Check and load config
    if not os.path.exists(args.config):
        LOG.error('Config JSON file not found: %s', args.config)
        raise RuntimeError()

    LOG.info('Loading configurations')
    with open(args.config, 'r') as filep:
        try:
            config = json.load(filep)
        except ValueError as err:
            LOG.error('Failed to load config: %s', str(err))
            raise RuntimeError()

    if not check_config(config):
        LOG.error('Config %s is invalid', args.config)
        raise RuntimeError()

    # Initialize database
    db = RedisDatabase(config['main.project-name'], os.path.join(config.work_dir, 'result.db'))

    # Initialize evaluator
    merlin_eval = MerlinEvaluator(
        config.src_path, config.work_path, EvalMode(config['evaluator.estimation']), db,
        PythonSubprocessScheduler(config['evaluator.max-worker-per-part']), MerlinAnalyzer,
        BackupMode(config['evaluator.backup']))

    # Compile design space
    LOG.info('Compiling design space')
    ds = compile_design_space(config['design-space.definition'])
    if ds is None:
        LOG.error('Failed to compile design space')
        raise RuntimeError()

    # Partition design space
    # TODO: profiling and pruning
    ds_list = partition(ds, int(config['design-space.max-partition']))


# Launch the DSE flow
main()

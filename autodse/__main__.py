"""
The main DSE flow that integrates all modules
"""
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List
import argparse
import json
import os
import shutil
import time

from autodse.config import build_config
from .logger import get_default_logger
from .database import Database, RedisDatabase
from .dsproc.dsproc import compile_design_space, partition
from .parameter import DesignSpace
from .evaluator.analyzer import MerlinAnalyzer
from .evaluator.evaluator import BackupMode, EvalMode, Evaluator, MerlinEvaluator
from .evaluator.scheduler import PythonSubprocessScheduler
from .explorer.explorer import Explorer

ARG_PARSER = argparse.ArgumentParser(description='Automatic Design Space Exploration')
ARG_PARSER.add_argument('--src-dir', action='store', help='Merlin project directory')
ARG_PARSER.add_argument('--work-dir', action='store', default='.', help='DSE working directory')
ARG_PARSER.add_argument('--config', action='store', help='path to the configure JSON file')
ARGS = ARG_PARSER.parse_args()

LOG = get_default_logger('Main')


def launch_exploration(ds_list: List[DesignSpace], db: Database, evaluator: Evaluator,
                       config: Dict[str, Any]):
    """Launch exploration"""

    pool = []

    # Launch a thread pool
    dse('part0', ds_list[0], db, evaluator, config)


#    with ThreadPoolExecutor(max_workers=len(ds_list)) as executor:
#        for idx, ds in enumerate(ds_list):
#            pool.append(
#                executor.submit(dse,
#                                tag='part{0}'.format(idx),
#                                ds=ds,
#                                db=db,
#                                evaluator=evaluator,
#                                config=config))
#
#    cnt = 0
#    while any([not exe.done() for exe in pool]):
#        time.sleep(1)
#        if cnt % 10 == 0:
#            LOG.info('10 seconds passed')
#        cnt = 0 if cnt == 10 else cnt + 1


def dse(tag: str, ds: DesignSpace, db: Database, evaluator: Evaluator, config: Dict[str, Any]):
    """Perform DSE for a given design space"""

    explorer = Explorer(ds=ds,
                        db=db,
                        evaluator=evaluator,
                        timeout=config['timeout']['exploration'],
                        tag=tag)
    explorer.run(config['search']['algorithm'])


def main() -> None:
    """The main function of the DSE flow"""

    src_dir = os.path.abspath(ARGS.src_dir)
    work_dir = os.path.abspath(ARGS.work_dir)

    # Check and load config
    if not os.path.exists(ARGS.config):
        LOG.error('Config JSON file not found: %s', ARGS.config)
        raise RuntimeError()

    LOG.info('Loading configurations')
    with open(ARGS.config, 'r') as filep:
        try:
            user_config = json.load(filep)
        except ValueError as err:
            LOG.error('Failed to load config: %s', str(err))
            raise RuntimeError()

    config = build_config(user_config)
    if config is None:
        LOG.error('Config %s is invalid', ARGS.config)
        raise RuntimeError()

    # Initialize workspace
    if not os.path.exists(src_dir):
        LOG.error('Project folder not found: %s', src_dir)
        raise RuntimeError()

    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.mkdir(work_dir)

    # Initialize database
    LOG.info('Initializing the system')
    db = RedisDatabase(config['project']['name'], os.path.join(work_dir, 'result.db'))

    # Initialize evaluator
    merlin_eval = MerlinEvaluator(src_path=src_dir,
                                  work_path=os.path.join(work_dir, 'evaluate'),
                                  mode=EvalMode[config['evaluate']['estimate-mode']],
                                  db=db,
                                  scheduler=PythonSubprocessScheduler(
                                      config['evaluate']['worker-per-part']),
                                  analyzer_cls=MerlinAnalyzer,
                                  backup_mode=BackupMode[config['project']['backup']])
    merlin_eval.set_timeout(config['timeout'])
    merlin_eval.set_command(config['evaluate']['command'])

    # Compile design space
    LOG.info('Compiling design space')
    ds = compile_design_space(config['design-space']['definition'])
    if ds is None:
        LOG.error('Failed to compile design space')
        raise RuntimeError()

    # Partition design space
    LOG.info('Partitioning the design space to at maximum %d parts',
             int(config['design-space']['max-part-num']))
    ds_list = partition(ds, int(config['design-space']['max-part-num']))
    if ds_list is None:
        LOG.error('No design space partition is available for exploration')
        raise RuntimeError()
    LOG.info('%d parts generated', len(ds_list))

    # TODO: profiling and pruning

    # Launch exploration
    try:
        LOG.info('Start the exploration')
        launch_exploration(ds_list, db, merlin_eval, config)
    except KeyboardInterrupt:
        pass

    LOG.info('Finish the exploration')

    # Report and summary
    db.persist()


# Launch the DSE flow
main()

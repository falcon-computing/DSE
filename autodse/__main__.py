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
from .reporter import Reporter
from .evaluator.analyzer import MerlinAnalyzer
from .evaluator.evaluator import BackupMode, EvalMode, Evaluator, MerlinEvaluator
from .evaluator.scheduler import PythonSubprocessScheduler
from .explorer.explorer import Explorer

ARG_PARSER = argparse.ArgumentParser(description='Automatic Design Space Exploration')
ARG_PARSER.add_argument('--src-dir',
                        required=True,
                        action='store',
                        help='Merlin project directory')
ARG_PARSER.add_argument('--work-dir',
                        required=True,
                        action='store',
                        default='.',
                        help='DSE working directory')
ARG_PARSER.add_argument('--config',
                        required=True,
                        action='store',
                        help='path to the configure JSON file')
ARG_PARSER.add_argument('--db',
                        required=False,
                        action='store',
                        default='',
                        help='path to the result database')
ARGS = ARG_PARSER.parse_args()

LOG = get_default_logger('Main')


def launch_exploration(ds_list: List[DesignSpace], db: Database, evaluator: Evaluator,
                       reporter: Reporter, config: Dict[str, Any]) -> None:
    """Launch exploration"""

    pool = []

    # Launch a thread pool
    with ThreadPoolExecutor(max_workers=len(ds_list)) as executor:
        for idx, ds in enumerate(ds_list):
            pool.append(
                executor.submit(dse,
                                tag='part{0}'.format(idx),
                                ds=ds,
                                db=db,
                                evaluator=evaluator,
                                config=config))

        LOG.info('%d explorers have been launched', len(pool))

        timer: float = 0  # in minutes
        while any([not exe.done() for exe in pool]):
            time.sleep(1)
            reporter.log_best()
            reporter.print_status(timer)
            timer += 0.0167


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
    out_dir = os.path.join(work_dir, 'output')
    if ARGS.db:
        db_path = os.path.abspath(ARGS.db)
    else:
        db_path = os.path.join(work_dir, 'result.db')

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

    if not os.path.exists(src_dir):
        LOG.error('Project folder not found: %s', src_dir)
        raise RuntimeError()

    # Initialize database
    LOG.info('Initializing the database')
    db = RedisDatabase(config['project']['name'], int(config['project']['output-num']), db_path)

    # Initialize workspace
    LOG.info('Initializing the workspace')
    if work_dir == os.getcwd():
        shutil.rmtree('*')
    else:
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        os.makedirs(work_dir)

    # Initialize evaluator
    LOG.info('Initializing the evaluator with evaluate mode %s and back mode %s',
             config['evaluate']['estimate-mode'], config['project']['backup'])
    merlin_eval = MerlinEvaluator(src_path=src_dir,
                                  work_path=os.path.join(work_dir, 'evaluate'),
                                  mode=EvalMode[config['evaluate']['estimate-mode']],
                                  db=db,
                                  scheduler=PythonSubprocessScheduler(
                                      config['evaluate']['worker-per-part']),
                                  analyzer_cls=MerlinAnalyzer,
                                  backup_mode=BackupMode[config['project']['backup']],
                                  dse_config=config['evaluate'])
    merlin_eval.set_timeout(config['timeout'])
    merlin_eval.set_command(config['evaluate']['command'])

    # Initialize reporter
    reporter = Reporter(config, db)

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

    #with open('ds_part{0}.json'.format(idx), 'w') as filep:
    #    filep.write(json.dumps({n: p.__dict__ for n, p in ds.items()}, sort_keys=True, indent=4))

    LOG.info('%d parts generated', len(ds_list))

    # TODO: profiling and pruning

    # Launch exploration
    try:
        LOG.info('Start the exploration')
        launch_exploration(ds_list, db, merlin_eval, reporter, config)
    except KeyboardInterrupt:
        pass

    LOG.info('Finish the exploration')

    # Create outputs
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    output = []
    for idx, (_, result) in enumerate(db.best_cache):
        job = merlin_eval.create_job()
        if not job:
            raise RuntimeError()

        assert result.point is not None
        merlin_eval.apply_design_point(job, result.point)
        os.rename(job.path, os.path.join(out_dir, str(idx)))
        result.path = str(idx)
        output.append(result)

    rpt = reporter.report_output(output)
    if rpt:
        with open(os.path.join(out_dir, 'output.rpt', 'w')) as filep:
            filep.write(rpt)

    # Report and summary
    db.persist()


# Launch the DSE flow
main()

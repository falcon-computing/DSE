"""
The main DSE flow that integrates all modules
"""
import argparse
import glob
import json
import os
import shutil
import tempfile
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from queue import PriorityQueue
from typing import Any, Dict, List, Optional, Set

from .config import build_config
from .database import Database, RedisDatabase
from .dsproc.dsproc import compile_design_space, partition
from .evaluator.analyzer import MerlinAnalyzer
from .evaluator.evaluator import (BackupMode, EvalMode, Evaluator, MerlinEvaluator)
from .evaluator.scheduler import PythonSubprocessScheduler
from .explorer.explorer import Explorer
from .logger import get_default_logger
from .parameter import DesignSpace
from .reporter import Reporter


def arg_parser() -> argparse.Namespace:
    """Parse user arguments."""

    parser = argparse.ArgumentParser(description='Automatic Design Space Exploration')
    parser.add_argument('--src-dir',
                        required=True,
                        action='store',
                        help='Merlin project directory')
    parser.add_argument('--work-dir',
                        required=True,
                        action='store',
                        default='.',
                        help='DSE working directory')
    parser.add_argument('--config',
                        required=True,
                        action='store',
                        help='path to the configure JSON file')
    parser.add_argument('--db',
                        required=False,
                        action='store',
                        default='',
                        help='path to the result database')
    parser.add_argument('--check-mode',
                        required=False,
                        action='store',
                        default='off',
                        help='only check the design space definition without running DSE')

    return parser.parse_args()


class Main():
    """The main class of DSE flow"""

    def __init__(self):
        self.start_time = time.time()
        self.args = arg_parser()

        # Validate check mode
        self.args.check_mode = self.args.check_mode.lower()
        if self.args.check_mode not in ['off', 'fast', 'complete']:
            print('Error: Invalid check-mode: %s. Must be either "off", "fast", or "complete"',
                  self.args.check_mode)
            raise RuntimeError()

        # Processing path and directory
        self.src_dir = os.path.abspath(self.args.src_dir)
        self.work_dir = os.path.abspath(self.args.work_dir)
        self.out_dir = os.path.join(self.work_dir, 'output')
        self.eval_dir = os.path.join(self.work_dir, 'evaluate')
        self.log_dir = os.path.join(self.work_dir, 'logs')
        if self.args.check_mode == 'complete':
            self.db_path = os.path.join(self.work_dir, 'check.db')
        elif self.args.db:
            self.db_path = os.path.abspath(self.args.db)
        else:
            self.db_path = os.path.join(self.work_dir, 'result.db')
        self.cfg_path = os.path.abspath(self.args.config)

        dir_prefix = os.path.commonprefix([self.src_dir, self.work_dir])
        if dir_prefix in [self.src_dir, self.work_dir]:
            print('Error: Merlin project and workspace cannot be subdirectories!')
            raise RuntimeError()
        if not os.path.exists(self.src_dir):
            print('Error: Project folder not found: %s', self.src_dir)
            raise RuntimeError()

        # Initialize workspace
        # Note that the log file must be created after workspace initialization
        # so any message before this point will not be logged.
        bak_dir = self.init_workspace()
        self.log = get_default_logger('Main')
        if bak_dir is not None:
            self.log.warning('Workspace is not empty, backup files to %s', bak_dir)
        self.log.info('Workspace initialized')

        # Check and load config
        self.config = self.load_config()

        # Stop here if we only need to check the design space definition
        if self.args.check_mode == 'fast':
            self.log.warning('Check mode "FAST": Only check design space syntax and type')
            return

        # Hack the config for check mode:
        # 1) Use exhaustive algorithm that always evaluates the default point first
        # 2) Set the exploration time to <1 second so it will only explore the default point
        # TODO: Check the bitgen execution
        if self.args.check_mode == 'complete':
            self.log.warning('Check mode "COMPLETE":')
            self.log.warning('1. Check design space syntax and type')
            self.log.warning('2. Evaluate one default point (may take up to 30 mins)')
            self.config['search']['algorithm']['name'] = 'exhaustive'
            self.config['timeout']['exploration'] = 0.01

            # We leverage this log to check the evaluation result so it has to be up-to-date
            if os.path.exists('eval.log'):
                os.remove('eval.log')

        # Initialize database
        self.log.info('Initializing the database')
        self.db = RedisDatabase(self.config['project']['name'],
                                int(self.config['project']['output-num']), self.db_path)
        self.db.load()

        # Initialize evaluator
        self.log.info('Initializing the evaluator')
        self.evaluator = MerlinEvaluator(src_path=self.src_dir,
                                         work_path=self.eval_dir,
                                         mode=EvalMode[self.config['evaluate']['estimate-mode']],
                                         db=self.db,
                                         scheduler=PythonSubprocessScheduler(
                                             self.config['evaluate']['worker-per-part']),
                                         analyzer_cls=MerlinAnalyzer,
                                         backup_mode=BackupMode[self.config['project']['backup']],
                                         dse_config=self.config['evaluate'])
        self.evaluator.set_timeout(self.config['timeout'])
        self.evaluator.set_command(self.config['evaluate']['command'])

        # Initialize reporter
        self.reporter = Reporter(self.config, self.db)

        if self.args.check_mode == 'off':
            self.log.info('Building the scope map')
            self.evaluator.build_scope_map()

            # Display important configs
            self.reporter.log_config()

    def init_workspace(self) -> Optional[str]:
        """Initialize the workspace

        Returns
        ------
        Optional[str]:
            The backup directory if available.
        """

        bak_dir: Optional[str] = None
        try:
            old_files = os.listdir(self.work_dir)
            if old_files:
                bak_dir = tempfile.mkdtemp(prefix='bak_', dir='.')

                # Move all files except for config and database files to the backup directory
                for old_file in old_files:
                    # Skip the backup directory of previous runs
                    if old_file.startswith('bak_'):
                        continue
                    full_path = os.path.join(self.work_dir, old_file)
                    if full_path not in [self.cfg_path, self.db_path]:
                        shutil.move(full_path, bak_dir)
        except FileNotFoundError:
            os.makedirs(self.work_dir)

        return bak_dir

    def load_config(self) -> Dict[str, Any]:
        """Load the DSE config"""

        if not os.path.exists(self.args.config):
            self.log.error('Config JSON file not found: %s', self.args.config)
            raise RuntimeError()

        self.log.info('Loading configurations')
        with open(self.args.config, 'r') as filep:
            try:
                user_config = json.load(filep)
            except ValueError as err:
                self.log.error('Failed to load config: %s', str(err))
                raise

        config = build_config(user_config)
        if config is None:
            self.log.error('Config %s is invalid', self.args.config)
            raise RuntimeError()

        return config

    def gen_outputs(self) -> None:
        """Generate final outputs"""

        # Clean output directory
        if os.path.exists(self.out_dir):
            shutil.rmtree(self.out_dir)
        os.makedirs(self.out_dir)

        # Fetch database cache for the best results
        output = []
        idx = 0
        best_cache: PriorityQueue = self.db.best_cache
        while not best_cache.empty():
            _, _, result = best_cache.get()
            job = self.evaluator.create_job()
            if not job:
                raise RuntimeError()

            assert result.point is not None
            self.evaluator.apply_design_point(job, result.point)
            os.rename(job.path, os.path.join(self.out_dir, str(idx)))
            result.path = str(idx)
            output.append(result)
            idx += 1

        rpt = self.reporter.report_output(output)
        if rpt:
            with open(os.path.join(self.out_dir, 'output.rpt'), 'w') as filep:
                filep.write(rpt)

    def launch_exploration(self, ds_list: List[DesignSpace]) -> None:
        """Launch exploration"""

        pool = []

        # Launch a thread pool
        with ThreadPoolExecutor(max_workers=len(ds_list)) as executor:
            for idx, ds in enumerate(ds_list):
                pool.append(
                    executor.submit(self.dse,
                                    tag='part{0}'.format(idx),
                                    ds=ds,
                                    db=self.db,
                                    evaluator=self.evaluator,
                                    config=self.config))

            self.log.info('%d explorers have been launched', len(pool))

            timer: float = (time.time() - self.start_time) / 60.0  # in minutes
            while any([not exe.done() for exe in pool]):
                time.sleep(1)
                while self.db.best_cache.qsize() > self.db.best_cache_size:
                    self.db.best_cache.get()
                self.reporter.log_best()
                self.reporter.print_status(timer)
                timer += 0.0167

    @staticmethod
    def dse(tag: str, ds: DesignSpace, db: Database, evaluator: Evaluator, config: Dict[str, Any]):
        """Perform DSE for a given design space"""

        explorer = Explorer(ds=ds,
                            db=db,
                            evaluator=evaluator,
                            timeout=config['timeout']['exploration'],
                            tag=tag)
        try:
            explorer.run(config['search']['algorithm'])
        except Exception as err:  # pylint:disable=broad-except
            log = get_default_logger('DSE')
            log.error('Encounter error during the exploration: %s', str(err))
            log.error(traceback.format_exc())

    def main(self) -> None:
        """The main function of the DSE flow"""

        # Compile design space
        self.log.info('Compiling design space')
        ds = compile_design_space(
            self.config['design-space']['definition'],
            self.evaluator.scope_map if self.args.check_mode == 'off' else None)
        if ds is None:
            self.log.error('Failed to compile design space')
            return

        # Partition design space
        self.log.info('Partitioning the design space to at maximum %d parts',
                      int(self.config['design-space']['max-part-num']))
        ds_list = partition(ds, int(self.config['design-space']['max-part-num']))
        if ds_list is None:
            self.log.error('No design space partition is available for exploration')
            return

        #with open('ds_part{0}.json'.format(idx), 'w') as filep:
        #    filep.write(
        #        json.dumps({n: p.__dict__
        #                    for n, p in ds.items()}, sort_keys=True, indent=4))

        self.log.info('%d parts generated', len(ds_list))

        if self.args.check_mode == 'fast':
            self.log.info('Finish checking the design space (fast mode)')
            return

        # TODO: profiling and pruning

        # Launch exploration
        try:
            if self.args.check_mode == 'off':
                self.log.info('Start the exploration')
            self.launch_exploration(ds_list)
        except KeyboardInterrupt:
            pass

        if self.args.check_mode == 'complete':
            if not os.path.exists('eval.log'):
                self.log.error('Evaluation failure')
            else:
                log_msgs: Set[str] = set()
                with open('eval.log', 'r') as filep:
                    for line in filep:
                        if line.find('ERROR') != -1:
                            msg = line[line.find(':') + 2:-1]
                            if msg not in log_msgs:
                                self.log.error(msg)
                                log_msgs.add(msg)
            self.log.info('Finish checking the design space (complete mode)')
            return

        self.log.info('Finish the exploration')

        # Backup database
        self.db.commit_best()
        self.db.persist()

        # Report and summary
        summary, detail = self.reporter.report_summary()
        for line in summary.split('\n'):
            if line:
                self.log.info(line)
        with open(os.path.join(self.work_dir, 'summary.rpt'), 'w') as filep:
            filep.write(summary)
            filep.write('\n\n')
            filep.write(detail)

        # Create outputs
        self.gen_outputs()
        self.log.info('Outputs are generated')

        # Backup logs
        if os.path.exists(self.log_dir):
            shutil.rmtree(self.log_dir)
        os.makedirs(self.log_dir)

        for log in glob.glob('*.log'):
            shutil.move(log, os.path.join(self.log_dir, log))

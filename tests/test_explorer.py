"""
The unit test module for explorer
"""

from autodse import logger
from autodse.database import Database
from autodse.evaluator import analyzer, scheduler
from autodse.evaluator.evaluator import BackupMode, Evaluator
from autodse.explorer.algorithm import SearchAlgorithm
from autodse.explorer.explorer import AccurateExplorer, FastExplorer
from autodse.result import Job, Result

LOG = logger.get_default_logger('UNIT-TEST', 'DEBUG')


def test_fast_explorer(mocker):
    #pylint:disable=missing-docstring

    with mocker.patch.object(Database, '__init__', return_value=None), \
         mocker.patch.object(Evaluator, '__init__', return_value=None), \
         mocker.patch.object(SearchAlgorithm, '__init__', return_value=None):

        # Fake a search algorithm generator
        mock_make = mocker.patch('autodse.explorer.algorithmfactory.AlgorithmFactory.make')
        fake_points = []
        for i in range(1, 9):
            fake_points.append({'A': i})
        mock_make.return_value.gen.return_value.send.return_value = fake_points

        # Algorithm config, although we will not use it in this test
        config = {'name': 'exhaustive', 'exhaustive': {'batch-size': 8}}

        db = Database('test')

        # Database returns value meaning all points are duplicated
        with mocker.patch.object(db, 'commit', return_value=None), \
             mocker.patch.object(db, 'batch_query', return_value=[Result()] * 8):
            evaluator = Evaluator('', '', db, scheduler.Scheduler(), analyzer.MerlinAnalyzer,
                                  BackupMode.NO_BACKUP, {})
            explr = FastExplorer(db, evaluator, 0.02, 'expr', {})
            explr.run(config)
            assert explr.explored_point == 0, 'Shoud not evaluate any new points'

        # Test point submission
        fake_submit_returns = []
        for i in range(1, 9):
            result = Result()
            result.valid = True
            result.quality = 8 - i
            if i % 2:  # Make a half of them eraly reject
                result.ret_code = Result.RetCode.EARLY_REJECT
            fake_submit_returns.append(('A-{}'.format(i), result))
        with mocker.patch.object(db, 'commit', return_value=None), \
             mocker.patch.object(db, 'batch_query', return_value=[None] * 8), \
             mocker.patch.object(Evaluator, 'create_job', return_value=Job('')), \
             mocker.patch.object(Evaluator, 'submit', return_value=fake_submit_returns):
            evaluator = Evaluator('', '', db, scheduler.Scheduler(), analyzer.MerlinAnalyzer,
                                  BackupMode.NO_BACKUP, {})

            # Fail to apply design point
            with mocker.patch('autodse.evaluator.evaluator.Evaluator.apply_design_point',
                              return_value=False):
                explr = FastExplorer(db, evaluator, 0.02, 'fast', {})
                explr.run(config)
                assert explr.explored_point == 0, 'Should not successfully explore any point'

            # Success running
            # Note that we mock the batch_query to pretend the fake points are not duplicated
            with mocker.patch('autodse.evaluator.evaluator.Evaluator.apply_design_point',
                              return_value=True):
                explr = FastExplorer(db, evaluator, 0.02, 'fast', {})
                explr.run(config)
                assert explr.explored_point > 100, 'Should explore many points'


def test_accurate_explorer(mocker):
    #pylint:disable=missing-docstring

    with mocker.patch.object(Database, '__init__', return_value=None), \
         mocker.patch.object(Evaluator, '__init__', return_value=None):

        # Algorithm config, although we will not use it in this test
        config = {'name': 'exhaustive', 'exhaustive': {'batch-size': 8}}

        db = Database('test')

        # Make up design points
        points = []
        for i in range(1, 9):
            points.append({'A': i})

        def mock_submit(jobs, eval_lv):
            #pylint:disable=missing-docstring, unused-argument
            return [('unused_key', Result())] * len(jobs)

        # Test point submission
        with mocker.patch.object(db, 'commit', return_value=None), \
             mocker.patch.object(Evaluator, 'create_job', return_value=Job('')), \
             mocker.patch('autodse.evaluator.evaluator.Evaluator.apply_design_point',
                          return_value=True):
            evaluator = Evaluator('', '', db, scheduler.Scheduler(), analyzer.MerlinAnalyzer,
                                  BackupMode.NO_BACKUP, {})

            with mocker.patch.object(evaluator, 'submit', side_effect=mock_submit):
                explr = AccurateExplorer(db, evaluator, 'accurate', points)
                explr.run(config)
                assert explr.explored_point == 8

"""
The unit test module for explorer
"""

from autodse import logger
from autodse.database import Database
from autodse.evaluator import analyzer, scheduler
from autodse.evaluator.evaluator import BackupMode, EvalMode, Evaluator
from autodse.explorer.algorithm import SearchAlgorithm
from autodse.explorer.explorer import Explorer
from autodse.result import Job, Result

LOG = logger.get_default_logger('UNIT-TEST', 'DEBUG')


def test_explorer(mocker):
    #pylint:disable=missing-docstring

    with mocker.patch.object(Database, '__init__', return_value=None), \
         mocker.patch.object(Evaluator, '__init__', return_value=None), \
         mocker.patch.object(SearchAlgorithm, '__init__', return_value=None), \
         mocker.patch('autodse.parameter.gen_key_from_design_point', return_value='a'):

        # Fake a search algorithm generator
        mock_make = mocker.patch('autodse.explorer.algorithmfactory.AlgorithmFactory.make')
        mock_make.return_value.gen.return_value.send.return_value = [{'A': 1}] * 8

        # Algorithm config, although we will not use it in this test
        config = {'name': 'exhaustive', 'exhaustive': {'batch-size': 8}}

        db = Database('test')

        # Database returns value meaning all points are duplicated
        with mocker.patch.object(db, 'batch_query', return_value=[Result()] * 8):
            evaluator = Evaluator('', '', EvalMode.FAST, db, scheduler.Scheduler(),
                                  analyzer.MerlinAnalyzer, BackupMode.NO_BACKUP, {})
            explr = Explorer({}, db, evaluator, 0.02)
            explr.run(config)
            assert explr.explored_point > 100, 'Should explore many points'

        # Test point submission
        fake_submit_returns = []
        for i in range(8):
            result = Result()
            result.valid = True
            result.quality = 8 - i
            fake_submit_returns.append((str(i), result))
        with mocker.patch.object(db, 'batch_query', return_value=[None] * 8), \
             mocker.patch.object(Evaluator, 'create_job', return_value=Job('')), \
             mocker.patch.object(Evaluator, 'submit', return_value=fake_submit_returns):
            evaluator = Evaluator('', '', EvalMode.FAST, db, scheduler.Scheduler(),
                                  analyzer.MerlinAnalyzer, BackupMode.NO_BACKUP, {})

            # Fail to apply design point
            with mocker.patch('autodse.evaluator.evaluator.Evaluator.apply_design_point',
                              return_value=False):
                explr = Explorer({}, db, evaluator, 0.02)
                explr.run(config)
                assert explr.explored_point == 8, 'Sould stop at the first iteration'

            # Success running
            with mocker.patch('autodse.evaluator.evaluator.Evaluator.apply_design_point',
                              return_value=True):
                explr = Explorer({}, db, evaluator, 0.02)
                explr.run(config)
                assert explr.explored_point > 100, 'Should explore many points'

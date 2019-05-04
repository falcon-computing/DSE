"""
The unit test module for explorer
"""

from autodse import logger
from autodse.database import Database
from autodse.evaluator import analyzer, scheduler
from autodse.evaluator.evaluator import BackupMode, EvalMode, Evaluator
from autodse.explorer.algorithm import SearchAlgorithm
from autodse.explorer.explorer import Explorer
from autodse.result import Job, ResultBase

LOG = logger.get_default_logger('UNIT-TEST', 'DEBUG')


def test_explorer(mocker):
    #pylint:disable=missing-docstring

    with mocker.patch.object(Database, '__init__', return_value=None), \
         mocker.patch.object(Evaluator, '__init__', return_value=None), \
         mocker.patch.object(SearchAlgorithm, '__init__', return_value=None), \
         mocker.patch('autodse.parameter.gen_key_from_design_point', return_value='a'), \
         mocker.patch('autodse.explorer.algorithmfactory.AlgorithmFactory.make'), \
         mocker.patch('autodse.explorer.algorithm.SearchAlgorithm.gen') as mock_gen:

        # Algorithm config, although we will not use it in this test
        config = {'name': 'exhaustive', 'exhaustive': {'batch-size': 8}}

        # Fake a search algorithm generator
        mock_gen.send = lambda x: [{'A': 1}] * 8

        # Database returns value meaning all points are duplicated
        with mocker.patch.object(Database, 'batch_query', return_value=[ResultBase()] * 8):
            db = Database('test')
            evaluator = Evaluator('', '', EvalMode.FAST, db, scheduler.Scheduler(),
                                  analyzer.MerlinAnalyzer, BackupMode.NO_BACKUP)
            explr = Explorer({}, db, evaluator, 0.05)
            explr.run(config)

        ## Test point submission
        with mocker.patch.object(Database, 'batch_query', return_value=[None] * 8), \
             mocker.patch.object(Evaluator, 'create_job', return_value=Job('')), \
             mocker.patch.object(Evaluator, 'apply_design_point', return_value=None), \
             mocker.patch.object(Evaluator, 'submit', return_value=[ResultBase()] * 8):
            db = Database('test')
            evaluator = Evaluator('', '', EvalMode.FAST, db, scheduler.Scheduler(),
                                  analyzer.MerlinAnalyzer, BackupMode.NO_BACKUP)
            explr = Explorer({}, db, evaluator, 0.05)
            explr.run(config)

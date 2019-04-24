"""
Common fixtures for testing
"""

import os

import pytest


@pytest.fixture(scope="module", autouse=True)
def prepare_fixture_files(request):
    root_dir = request.fspath.join('..')
    if not os.path.exists('{0}/fixture'.format(root_dir)):
        os.system('tar -xzf {0}/fixture_files.tgz -C {0}/'.format(root_dir))


@pytest.fixture(scope="module")
def test_dir(request):
    #pylint:disable=missing-docstring

    return request.fspath.join('..')

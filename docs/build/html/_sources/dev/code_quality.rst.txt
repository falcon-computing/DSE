Code Quality Assurance
======================

This page explains how to maintain the code quality
of this repository. Currently, we do not have an automation
to assure the following rules are satisfied, but this should
be covered in the future.

Coding Style
------------

This system is implemented in Python 3.6 and we basically follow
`PEP8 <https://www.python.org/dev/peps/pep-0008/>`_ standard
to unify the coding style. In addition, the following guides are defined
by ourselves:

- The max length of each line is 100 characters.
- The indent size is 4 spaces and no tabs are allowed.

Specifically, we use `pylint` for coding style validation:

.. code:: bash

    make lint

Look into the command in the Makefile, we can find that it uses a rc file
under `tests/lint/pylintrc`. This file defines all coding style rules
that will be checked by pylint.
**We require a perfect score rated by pylint and do not allow any
pylint messages.** It means everything specified in the rc file must be
strictly followed.

.. note::

    The rc file is slightly modified based on
    `TVM <https://github.com/dmlc/tvm>`_
    but it can be changed based on the usage. Please discuss with
    the team before making any change to the file.

Type Checking
-------------

It is important to statically check types before running a Python package,
because Python is basically type-free. Therefore, type annotation
was introduced in Python 3 to help both developers and checking tools resolve
as many type issues as possible before actual launching the program.
In Merlin DSE, we use `mypy` to statically check types.
**We also do not allow any warning and error messages from mypy,
but it is fine if they are from third-party packages.**

.. code:: bash

    make type

.. note::

    `mypy` checks types passively. It will not check types if no
    type annotations in Python file. As a result, please make sure
    to at least add type annotations to method arguments, and then
    `mypy` will be triggered and provide further information for missing
    type annotations to other variables.

Auto-Formatting
---------------

We use `yapf`, an auto-formatting package open source by Google, to auto-format
the code. Everyone should run this command before committing any changes.
The formatting style is defined at `tests/lint/yapf_style.cfg`.

.. code:: bash

    make format

.. note::

    It is possible to have conflicts between yapf style and pylint style,
    so please make sure they are conflict-free when making changes to
    either files.

Unit Test and Code Coverage
---------------------------

We use `pytest` as the unit test framework and test code coverage.
Use the following command to simply run all unit tests:

.. code:: bash

    make unit_test

The unit test should take less than one minute and you will see a handy report
to indicate the test results. If one or more tests were failed, you should
go back to fix the problem and run the test again. Note that when you run
the test again, it will only run the failed tests as we specified `--lf` in
the Makefile.

In addition, we also use `pytest` to measure the code coverage:

.. code:: bash

    make cov

The console output will indicate the number and percentage of
coverage statements in each file and an overall coverage rate.
Although we have not set a required coverage rate, it would
be good to achieve more than 85% or 90% for an entire package.

Walkthrough Codebase
====================

In this guide, we illustrate key modules of Merlin DSE.
For each important step, we show how the Merlin DSE modules works so that
the developers can dive into the codebase quickly.

Codebase Structure
------------------

At the root of Merlin DSE repository, we have a directory ``autodse`` that
includes all Python codebase.

- ``__init__.py``: The placeholder to tell Python interpreter the code in this
  directory is a Python module.
- ``__main__.py``: The entrypoint of this Python package.
- ``config.py``: All DSE configurations and their parser.
- ``database.py``: Result database implementation.
- ``logger.py``: Central logging system.
- ``main.py``: The actual main function of this package.
- ``parameter.py``: The definition of design parameters.
- ``reporter.py``: Display handy process and result messages to users.
- ``result.py``: The definitions of evaluation results.
- ``util.py``: Miscellaneous.
- ``dsproc``: Design space processor implementation.
- ``evaluator``: The evaluator implementation, including analyzer, evaluator
  and scheduler.
- ``explorer``: The explorer implementation, including explorer and algorithms.

Fast Mode DSE
-------------

We launch DSE fast mode and explain the execution flow:

.. code:: bash

    python3 -m autodse src work src/config.json fast-dse

Initialization
~~~~~~~~~~~~~~

- Python interpreter finds and execute ``__main__.py`` under ``autodse``.
- ``__main__.py`` invokes ``Main`` object defined in ``main.py``, which
  implements the main DSE flow.
- The constructor of ``Main`` initializes the workspace (``work`` in this
  example), ``Evaluator``, and ``Database``.
- ``Evaluator`` in ``evaluator/evaluator.py`` scans user kernel files and
  identifies the ones with ``auto{}`` keywords. If no keywords were found,
  then it errors out and terminates the process since we do not have design
  space to be explored.
- ``Database`` in ``database.py`` creates a new database using the project name
  and timestamp, and then checks if there has an existed materialized database
  file and loads data from it if so.

Design Space Compilation
~~~~~~~~~~~~~~~~~~~~~~~~

- It first uses ``compile_design_space`` implemented in ``dsproc/dsproc.py``
  to parse the design space in ``config.json`` and builds their dependencies.
- Then, it partitions the design space by invoking ``partition`` in
  ``dsproc/dsproc.py``.

Exploration
~~~~~~~~~~~

- After that, it launches ``Main.launch_fast``. This method uses Python thread
  pool executor to fork threads for partitions. Each thread executes
  ``fast_runner`` that creates a ``FastExplorer`` in ``explorer/explorer.py``
  to perform DSE in fast mode and keep tracking the progress.
- In ``FastExplorer.run()``, it creates an algorithm using algorithm factory
  in ``explorer/algorithmfactory.py`` that calls the suitable algorithm
  constructor (defined in ``config.json``).
- Every search algorithm has a method called ``gen`` that returns
  a generator. ``Explorer`` uses
  ``gen_next = AlgorithmFactory.make(...).gen()`` to obtain the generator.
- At the first iteration, the ``Explorer`` calls ``gen_next.send(None)`` to ask
  the search algorithm for the first batch design points.
- For each design point, ``Explorer`` creates a corresponding job and checks
  if it is duplicated in the database. It then submits non-duplicated points
  to ``Evaluator`` with `level 1` to run Merlin transformation.
- After the evaluation, ``Evaluator`` calls ``Analyzer`` in
  ``evaluator/analyzer.py`` to analyze level 1 results. Specifically, it checks
  if Merlin complains any inserted pragmas are ineffective, and set the return
  code to `EARLY_REJECT`.
- ``Explorer`` receives the results from ``Evaluator``, filters out
  the points with `EARLY_REJECT`, and submits rest points to ``Evaluator``
  again with `level 2` to run HLS.
- After the evaluation, ``Evaluator`` calls ``Analyzer`` in
  ``evaluator/analyzer.py`` to analyze level 2 results. Specifically, it checks
  if HLS was success or not. If it was success, analyzer further parses Merlin
  report to sort performance bottleneck paths.
- ``Explorer`` calls ``gen_next.send(results)`` again with the received
  results from ``Evaluator``.
- The search algorithm will return the next batch of design points according to
  the results it received.
- The above process will be performed iteratively until either the time limit
  or the search algorithm terminates.

Output
~~~~~~

- After the exploration and back to ``Main``, it persists the database
  to a binary file for future reference.
- Several ``Reporter`` methods are invoked to summarize the DSE process.
- ``gen_fast_outputs`` is invoked to dump the outputs of fast mode.

Accurate Mode DSE
-----------------

We then launch DSE accurate mode and explain the execution flow:

.. code:: bash

    python3 -m autodse src work src/config.json accurate-dse

Since the first part is same as the fast mode, we will start with the
accurate exploration directly.

Exploration
~~~~~~~~~~~

- Different from ``FastExplorer``, ``AccurateExplorer`` receives a small list
  of design points and explore them exhaustively.
- For each given design point, ``AccurateExplorer`` submits it to ``Evaluator``
  with `level 3`, which runs physical design flow and generates bit-stream.

Output
~~~~~~

- After the exploration, ``gen_accurate_outputs`` in ``Main`` copies the
  evaluated Merlin projects to the output directory and generates a report
  to summarize them.
- ``gen_accurate_outputs`` also creates a symbolic link named `best` from
  the evaluated design point project directory to the output directory.

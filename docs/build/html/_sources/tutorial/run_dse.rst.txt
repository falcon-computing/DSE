Run DSE Flow
============

This page explains how to run the DSE flow and read its reports and logs.

Docker Environment (Recommend)
------------------------------

DSE infrastructure provides a Dockerfile that has all required environment
ready. It is highly suggested run DSE in the docker container to enjoy the
following advantages:

- No worries about the DSE environment, Merlin compiler environment, and even
  vendor tool environment anymore.
- Easy-to-use builtin commands (see instructions below).
- All processes, including DSE processes, Merlin processes and vendor tool
  processes, are guaranteed to be terminated when the docker container is
  terminated.

Setup
~~~~~

1. Build Merlin docker image and make sure the image ``melrin:latest``
   is available in "docker image ls".
2. Build DSE docker image by running ``./docker-build.sh``
   and make sure the image ``merlin-dse:latest`` is available in
   ``docker image ls``.
3. Create a new container by running ``./docker/docker-run.sh /bin/bash``.
   Note that you need to be at the directory that contains both Merlin project
   and working directory when launching the container.

Execution
~~~~~~~~~

After entering to the container, you do not need to set up anything but can
directly use the builtin commands as follows to make use of the DSE.

.. note::
    You will still need to write a Python command to launch the DSE if you
    would like to use more advance run-time arguments
    (e.g., ``--disable-animation``).
    See the following for detail arguments.

Design Space Checker
    This command checks if your design space definition has any problems to
    save your time; otherwise you may wait for several hours of DSE and
    found that it did nothing due to an invalid design space definition.

    There have two checking modes to be used: fast and complete mode:

        fast:
            Check the syntax and data type of design space definition in
            the config file. It usually takes a second.

        complete:
            Check not only design space definition in config file
            but the kernel code. The errors such as missing/misspell
            parameter name or incorrect execution commands will be caught
            by this checking. Since it really runs HLS for one design point,
            it may take up to 30 minutes.

    The docker builtin commend is used as follows:

.. code:: bash

    checkds <source project dir> <working dir> <config file> <fast|complete>

Design Space Exploration
    This command launches the DSE. There have two modes to be used:
    fast and accurate mode:

    fast:
        Perform DSE with HLS result and output a number of points with high QoR
        in terms of HLS cycles.

    accurate:
        Perform fast mode, generates bit-streams for its outputs, and mark
        the one with the best QoR in terms of HLS cycle and working frequency.

    The docker commend is used as follows:

.. code:: bash

    autodse <source project dir> <working dir> <config file> <fast|accurate> [<database file>]

Host Machine
------------

Since the DSE flow is implemented as a standard Python package,
we can also execute it using Python interpreter directly:

1. Make sure Python 3.6+ is available.
2. Setup DSE package by running ``python3 setup.py``. This will install
   dependent packages and deploy our ``autodse`` package in the machine.
   Alternatively, you can also manually install dependent packages and add
   the directory that contains ``autodse`` to ``PYTHONPATH``.
3. Run the design space checker to make sure the design space definition is
   valid:

    .. code:: bash

        python3 -m autodse --src-dir <source project dir> --work-dir <working dir> --config <config file> --mode <fast-check|complete-check> [--disable-animation]

4. Run the DSE by launching the package. Note that the optional argument
   ``disable-animation`` will use dots instead of animation to indicate
   the DSE is still running.

    .. code:: bash

        python3 -m autodse --src-dir <source project dir> --work-dir <working dir> --config <config file> --db <database file> --mode <fast-dse|accurate-dse> [--disable-animation]

Outputs
-------

After the DSE is done, you will find some files in the working directory:

summary_fast.rpt
    The summary file that tells you how many points have been explored in the
    fast mode and their results. It also provides the detail of each point
    so that you could know more about the search process and your design.

summary_accurate.rpt
    The summary file that tells you how many points have been processed in
    the accurate mode and their results. It also provides the detail of each
    point so that you could know more about the search process and your design.

output
    The most important directory that contains the DSE output.

    best
        The symbolic link after the accurate mode pointing to the output
        project with the best design.

    fast
        The output of fast mode. It includes a report file ``output.rpt``
        telling you how many points we output and what are their quality.
        Each output is a valid Merlin project so you could continue working
        with it using the Merlin compiler.

        The output of fast mode also includes ``result_dist.pdf`` that draws
        valid HLS result on a performance-area chart. The chart also depicts
        a Pareto curve and shows Pareto efficient design points in the explored
        space.

    accurate
        The output of accurate mode. It includes a report file ``output.rpt``
        telling you how many points we perform P&R and what are their quality
        including working frequency and actual resource utilization.
        The bit-stream is also available is the point could pass P&R.

logs
    All DSE log files, including the logs of overall execution flow, evaluator,
    explorer and the search algorithm.

    dse.log
        The backup of all messages shown on the console.

    eval.log
        The log of evaluation, including how many jobs have be submitted and
        if they encounter any issues during the evaluation.

    partX_expr.log
        The log of explorer of design space partition X. It logged the time to
        find a better design point in the partition.

    partX_algo.log
        The log of search algorithm of design space partition X. The format
        and contents highly depend on the search algorithm. For example,
        ``exhaustive`` simply logs all explored points; ``gradient`` logs
        the process of design bottleneck analysis and important parameter
        identification. This log could be helpful for users to understand
        what DSE has done and if its exploration process makes sense or not.

results.db
    The dumped database with all evaluated results. You can simply reuse this
    database to continue launching the DSE if you want to explore using
    the fast mode again with more time.

bak_OOOOO
    The backup directory that contains all files in the working directory
    before launching the exploration.

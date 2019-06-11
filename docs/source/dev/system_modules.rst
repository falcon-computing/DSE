System and Modules
==================

This page introduces the Merlin DSE system and connections between modules.
The Merlin DSE infrastructure is composed of several building blocks.
We list them along with their tasks.

Design Space Processor
----------------------
- A set of static methods.
- Take the design space definition in user input ``config.json``.
- Parse and check design space.
- Partition and prune the design space.

Evaluator
---------
- Create and initialize jobs.
- Apply design point to a job.
- 3 level evaluation modes. Level 1 is the fastest but the most
  inaccurate mode, and vice versa.
- Submit jobs to the `Scheduler`_.
- Analyze results by calling `Analyzer`_.
- Commit results to the `Database`_.

MerlinEvaluator
    - Level 1: Run Merlin transformation and parse ``merlin.log`` to
      check if Merlin transformation was success or not.
    - Level 2: Run HLS and parse ``merlin.log`` and ``perf_est.json`` to
      analyze performance bottleneck.
    - Level 3: Run P&R to generate bitstream and parse ``merlin.log`` for
      working frequency and resource utilization.

Scheduler
---------
- Receive and execute jobs.

PythonSubprocessScheduler
    - Single node multithread.
    - Use Python subprocess package.

Analyzer
--------
- Define required files for analysis

MerlinAnalyzer
    - Analyze ``merlin.log`` for flow details.
    - Analyze Merlin report for QoR.

Explorer
--------
- Launch search algorithm.
- Submit design points to `Evaluator`_.
- Feedback results to the `Algorithm`_.

FastExplorer
    - Use level 1 evaluation for design points and skip the points
      with ``EARLY_REJECT`` status, because they encountered the failure
      of Merlin transformation due to an ineffective pragma combination.
    - Use level 2 evaluation for rest design points.

AccurateExplorer
    - Use level 3 evaluation for all points.

Algorithm
---------
- Search design space.
- Output a set of points iteratively.
- Receive evaluation results.

Exhaustive
    - DFS search design space.

Gradient
    - Start from the default design point (search tree level 0).
    - Receive QoR and the design bottleneck from `Explorer`_.
    - Map the design bottleneck to design parameters and determine the
      search order.
    - Start from the design parameter with the highest order,
      search all its options in parallel. The available options are
      appended to the next level in the search tree.
    - Repeat the process until the search tree is empty or the search time
      limit.

Database
--------
- Load existed data
- Query, commit, persist
- Maintain the best QoR cache for reporting.

Redis Database
    - Widely-used NoSQL database
    - Lightweight and thread safe
    - Optimized efficiency

Pickle Database
    - The simplest NoSQL database implementation for Python.
    - Do not have builtin thread safe mechanism so we implemented it using
      Python thread lock.
    - Low efficiency.
    - Mainly for unit test.

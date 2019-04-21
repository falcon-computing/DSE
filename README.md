Merlin Design Space Exploration Infrastructure
==============================================

Execution
---------
Since the user execution flow has not yet been created, currently we could use Python REPL to test each module.
By simply adding `autodse` to `PYTHONPATH`, you can import the `autodse` package with `import autodse` in your
Python environment.

Virtual Python Environment (optional)
-------------------------------------
`make env`

Python Environment Compatibility Test
-------------------------------------
`make tox`

Code Linting
------------
`make lint`

Unit Tests
----------
`make unit_test`

Coverage Test
-------------
`make cov`

Document Generation
-------------------
`make doc`

System Requirements
-------------------
* Python 3.6+

* Redis database

Development Requirements
------------------------
* The requirement Python packages for developements are list in `dev_reqs.txt` and can be installed
by `pip install -r dev_reqs.txt`.

* This project can be developed with an IDE that supports Python (e.g., vscode) and all unit tests
can be executed on any machine (Windows or Linux).

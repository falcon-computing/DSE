Merlin Design Space Exploration Infrastructure
==============================================

Execution
---------
Since the user execution flow has not yet been created, currently we could use Python REPL to test each module.
By simply adding `autodse` to `PYTHONPATH`, you can import the `autodse` package:

```python
import autodse
from autodse import dsproc
```

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

Development Requirements
------------------------
The following Python packages are required for developement:
* setuptools
* pylint
* pytest
* pytest-cov
* Sphinx
* sphinx_rtd_theme
* autopep8

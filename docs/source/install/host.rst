
.. _install-on-host:

Install on Host
===============

This page gives instructions on how to build and install the
MerlinDSE package from scratch on Linux systems.

To get started, clone the repo from github.

.. code:: bash

    git clone https://github.com/falcon-computing/Merlin_DSE.git

Package Installation
~~~~~~~~~~~~~~~~~~~~

There are two ways to install the package:

Method 1
   This method is **recommended for developers** who may change the codes.

   Set the environment variable `PYTHONPATH` to tell python where to find
   the library. For example, assume we cloned `MerlinDSE` on the home directory
   `~`. then we can added the following line in `~/.bashrc`.
   The changes will be immediately reflected once you pull the code and rebuild
   the project (no need to call ``setup`` again).

   .. code:: bash

       export PYTHONPATH=$HOME/MerlinDSE:${PYTHONPATH}


Method 2
   Install the python bindings by `setup.py`:

   .. code:: bash

       # install package for the current user
       # NOTE: if you installed python via homebrew, --user is not needed during installaiton
       #       it will be automatically installed to your user directory.
       #       providing --user flag may trigger error during installation in such case.
       cd MerlinDSE; python3 setup.py install --user

Python dependencies
~~~~~~~~~~~~~~~~~~~
   * Necessary dependencies:

   .. code:: bash

       pip install -r dev_reqs.txt

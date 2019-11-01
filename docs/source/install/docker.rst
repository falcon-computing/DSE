
.. _install-on-docker:

Install on Docker
=================

This page gives instructions on how to directly use the
MerlinDSE package in dockers.

To get started, clone the repo from github.

.. code:: bash

    git clone https://github.com/falcon-computing/Merlin_DSE.git

We provide a docker file that includes all required depedencies and tools.
You can build the docker image via the following steps.

We can then use the following command to build a docker image:

.. code:: bash

    /path/to/MerlinDSE/docker/docker-build.sh

Note that you need to build a docker image for the Merlin compiler in advance.

After the image has been successfully built, you can create a container and
start using MerlinDSE. Note that you should be at the right directory that
can access your project and working space.

.. code:: bash

    /path/to/MerlinDSE/docker/docker-run.sh -i /bin/bash

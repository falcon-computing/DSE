Prepare a Project with a Design Space
=====================================

Preparation
-----------

- A `self-contained` Merlin project, including host and kernel programs.
  **Please make sure the Merlin project can pass the Merlin transformation
  and HLS before using the DSE**.
- Define a design space in the kernel program. See `Define a Design Space`_
  for details.
- A configuration file.

.. note::
    The working directory cannot under or cover the source project directory.
    The following cases are disallowed:

    .. code::

        project
        |- Makefile
        |- src
        |- work // Cannot under the source project directory!

    .. code::

        work // Cannot cover the source project directory!
        |- project
          |- src
          |- Makefile

Define a Design Space
---------------------

You need to define a valid design space in terms of positions and properties.
In this section, we will explain why and how to define them along with
a general matrix multiplication (GEMM) example for demonstration.

Positions
~~~~~~~~~

Please note that the Merlin DSE only explores the best combination of
pragma values, so you need to first determine the position of your
design spaces. For example, you could write parallel and pipeline pragmas
to the loop that you want to explore. When you are not sure if it is a good
idea to put the pragma there just put it first, and we will teach you in the
`Properties`_ section about how to add an option to turn off this pragma.

.. note::

    The automatic design space generator is also under development,
    but we suggest constructing a design space for your designs so that you
    could understand more about the search process.

Here we define the positions in the GEMM example:

.. code:: cpp

    for (int p = 0; p < 1024; ++p) {
        for (int q = 0; q < 1024; ++q)
            C[p][q] = 0;
    }

    #pragma ACCEL pipeline auto{K_PIPE}
    #pragma ACCEL parallel factor=auto{K_PAR}
    for (int k = 0; k < 1024; ++k) {
        #pragma ACCEL pipeline auto{I_PIPE}
        #pragma ACCEL parallel factor=auto{I_PAR}
        for (int i = 0; i < 1024; ++i) {
            #pragma ACCEL pipeline auto{J_PIPE}
            #pragma ACCEL parallel factor=auto{J_PAR}
            for (int j = 0; j < 1024; ++j) {
                C[i][j] += A[i][k] * B[k][j];
            }
        }
    }

We can see from above example that we added 6 Merlin pragmas to a 3-level
loop nest but left the most important pragma attribute undetermined.
Instead, we use ``auto{param_id}`` to define design space parameters and
the valid combinations of those 6 parameters form a design space.
The parameter ID is just like a unique variable name and can be defined
by yourself. Note that in this example we did not add any pragma to the first
loop for initializing array C because it looks not very important.

After the positions and parameters have been determined,
we move to the next step to define their properties.

Properties
~~~~~~~~~~

For each design parameter ID defined in the kernel program, we need to provide
the corresponding property in the config JSON file with the following fields:

.. code:: json

    {
        "<param_id>": {
            "options": "[x**2 for x in range(10)]",
            "order": "0 if x < 64 else 1",
            "ds_type": "PARALLEL",
            "default": 1
        }
    }

options (required)
    - This field describes the possible options of the design parameter.
      The syntax matches Python list comprehension which is easy to learn
      `here <https://www.pythonforbeginners.com/basics/list-comprehensions-in-python>`_.
    - Users should use single quotes to represent the constant string in
      the representation. For example:
      ``"options": "[x**2 for x in range(10) if x == 0 or ID2 == 'off']"``,
      where ``ID2`` is another design parameter and it may be ``"off"``
      sometimes.
    - The condition part in the list comprehension is optional and can depend
      on itself (e.g., ``[x for x in range if x > 5]``) or other parameters
      (e.g., ``[x for x in range if x == 0 or ID2 < 5]``).
    - The user has to guarantee the available option is always not empty.
      In other words, ``[x for x in range(10) if ID2 < 5]`` is invalid because
      the available option would be ``<null>`` when ``ID2`` is larger than 5.

order (optional)
    - This field describes the preference of searching order for
      this parameter. The syntax matches Python one-line if-statement.
    - This field should return an integer to indicate the priority of options.
      Note that 0 means the highest priority.
    - This is a reference for partitioning the design space and search
      algorithm. The DSE can still perform the search without this field.

ds_type (suggested)
    - This field describes the design space type of this parameter
      (e.g., ``PARALLEL``, ``PIPELINE``, ``INTERFACE``, etc).
    - This works as a hint to help search algorithm understand the design space
      and improve the search efficiency.
    - This is a reference for partitioning the design space and search
      algorithm. The DSE can still perform the search without this field.

default (required)
    - The field describes the default value of this design parameter.
    - The data type of this field must match the one in options.

We again define the design space property for the GEMM example:

.. code:: json

    {
        "design-space-definition": {
            "K_PIPE": {
                "options": "['off','','flatten']",
                "order": "0 if x == 'flatten' else 1",
                "ds_type": "PIPELINE",
                "default": "off"
            },
            "K_PAR": {
                "options": "[x**2 for x in range(11)]",
                "order": "0 if x < 64 else 1",
                "ds_type": "PARALLEL",
                "default": 1
            },
            "I_PIPE": {
                "options": "[x for x in ['off','','flatten'] if x=='off' or K_PIPE!='flatten']",
                "order": "0 if x == 'flatten' else 1",
                "ds_type": "PIPELINE",
                "default": "off"
            },
            "I_PAR": {
                "options": "[x**2 for x in range(11) if x==0 or K_PIPE!='flatten']",
                "ds_type": "PARALLEL",
                "default": 1
            },
            "J_PIPE": {
                "options": "[x for x in ['off',''] if x=='off' or (K_PIPE!='flatten' and I_PIPE!='flatten')]",
                "ds_type": "PIPELINE",
                "default": "off"
            },
            "J_PAR": {
                "options": "[x**2 for x in range(11) if x==0 or (K_PIPE!='flatten' and I_PIPE!='flatten')]",
                "ds_type": "PARALLEL",
                "default": 1
            }
        }
    }

Some highlights in this design space properties:

- ``K_PIPE`` and ``I_PIPE`` have the "order" field. It means we want to explore
  the combinations with their "flatten" option.
- ``K_PAR`` also has the "order" field. It means we want to explore <64 factors
  prior to other factors.
- ``I_PIPE`` and ``I_PAR`` has conditions ``x==? or K_PIPE!='flatten'``,
  which has the following semantics:

    - ``K_PIPE!='flatten'`` -> ``I_PIPE=['off', '', 'flatten']`` and
      ``I_PAR=[1,2,4,8,16,32,64,128,256,512,1024]``
    - ``K_PIPE=='flatten'`` -> ``I_PIPE=['off']`` and ``I_PAR=[1]``

After defining the design space properties, we put it to ``config.json``.
We are almost there! The final step before running the DSE is to add some
more configurations to control the DSE behavior, describing
in the next section.

Configurations
--------------

The DSE config file is in one-level JSON format so all configs are
key-value pairs. Here we list all available DSE configs. The value with
*def* indicates the default option. If no *def* in the value field, then
that configuration is required.

+--------------------+-----------------------+--------------------------------+
| Configuration      |      Value            |       Description              |
+====================+=======================+================================+
| project.           | "project" (def)       | The name of this project       |
| name               |                       | used as a tag.                 |
+--------------------+-----------------------+--------------------------------+
| project.           | - "NO_BACKUP"         | What kind of running           |
| backup             | - "BACKUP_ERROR" (def)| project should be kept.        |
|                    | - "BACKUP_ALL"        |                                |
+--------------------+-----------------------+--------------------------------+
| project.           | 4 (def)               | Number of output Merlin        |
| fast-output-num    |                       | projects in fast mode.         |
+--------------------+-----------------------+--------------------------------+
| timeout.           | Integer in minutes    | The target exploration         |
| exploration        |                       | time. Note that the            |
|                    |                       | actual exploration may         |
|                    |                       | be longer because we           |
|                    |                       | will not abandon the           |
|                    |                       | running jobs.                  |
+--------------------+-----------------------+--------------------------------+
| timeout.           | Integer in minutes    | The limit time to              |
| transform          |                       | perform Merlin                 |
|                    |                       | transformation.                |
+--------------------+-----------------------+--------------------------------+
| timeout.           | Integer in minutes    | The limit time to              |
| hls                |                       | perform HLS.                   |
+--------------------+-----------------------+--------------------------------+
| timeout.           | Integer in minutes    | The limit time to              |
| bitgen             |                       | perform P&R.                   |
+--------------------+-----------------------+--------------------------------+
| evaluate.          | Command string        | The command for running        |
| command.           |                       | Merlin transformation.         |
| transformation     |                       |                                |
+--------------------+-----------------------+--------------------------------+
| evaluate.          | Command string        | The command for running        |
| command.           |                       | HLS.                           |
| hls                |                       |                                |
+--------------------+-----------------------+--------------------------------+
| evaluate.          | Command string        | The command for running        |
| command.           |                       | P&R.                           |
| bitgen             |                       |                                |
+--------------------+-----------------------+--------------------------------+
| evaluate.          | 0.8 (def)             | The maximum allowed            |
| max-util.          |                       | utilization of BRAM.           |
| BRAM               |                       |                                |
+--------------------+-----------------------+--------------------------------+
| evaluate.          | 0.8 (def)             | The maximum allowed            |
| max-util.          |                       | utilization of DSP.            |
| DSP                |                       |                                |
+--------------------+-----------------------+--------------------------------+
| evaluate.          | 0.8 (def)             | The maximum allowed            |
| max-util.          |                       | utilization of LUT.            |
| LUT                |                       |                                |
+--------------------+-----------------------+--------------------------------+
| evaluate.          | 0.8 (def)             | The maximum allowed            |
| max-util.          |                       | utilization of FF.             |
| FF                 |                       |                                |
+--------------------+-----------------------+--------------------------------+
| search.            | "gradient" (def)      | The search algorithm           |
| algorithm.         | "exhaustive"          | to be used.                    |
| name               |                       |                                |
+--------------------+-----------------------+--------------------------------+
| search.            | 8 (def)               | The batch size of              |
| algorithm.         |                       | exhaustive search              |
| exhaustive.        |                       | algorithm.                     |
| batch-size         |                       |                                |
+--------------------+-----------------------+--------------------------------+
| search.            | 64 (def)              | The minimum latency            |
| algorithm.         |                       | threshold we want the          |
| gradient.          |                       | gradient algorithm to          |
| latency-threshold  |                       | improve.                       |
+--------------------+-----------------------+--------------------------------+
| search.            | true (def)            | Improve the performance        |
| algorithm.         |                       | from the innermost loop.       |
| gradient.          |                       |                                |
| fine-grained-first |                       |                                |
+--------------------+-----------------------+--------------------------------+
| search.            | "performance" (def)   | The quality function of        |
| algorithm.         | "finite-difference"   | gradient search.               |
| gradient.          | "resource-efficiency" | Perf.: 1/(latency or runtime); |
| quality-type       |                       | FD: Delta Perf / Resource Util;|
|                    |                       | RE: Perf/ Resource Util        |
+--------------------+-----------------------+--------------------------------+
| search.            | ["PARALLEL",          | The search order of design     |
| algorithm.         |  "PIPELINE"] (def)    | parameter type when the        |
| gradient.          |                       | performance bottlenck is       |
| compute-bound-order|                       | compute bound.                 |
+--------------------+-----------------------+--------------------------------+
| search.            | ["INTERFACE",         | The search order of design     |
| algorithm.         |  "CACHE",             | parameter type when the        |
| gradient.          |  "PIPELINE",          | performance bottlenck is       |
| memory-bound-order |  "TILING"] (def)      | memory bound.                  |
+--------------------+-----------------------+--------------------------------+
| design-space.      | 4 (def)               | The maximum no. allowed        |
| max-part-num       |                       | design space partitions.       |
+--------------------+-----------------------+--------------------------------+
| design-space.      | Dictionary            | The design space               |
| definition         |                       | definition.                    |
+--------------------+-----------------------+--------------------------------+

Again, this is one possible ``config.json`` for the GEMM example:

.. code:: json

    {
        "project.name": "gemm-blocked",
        "project.backup": "BACKUP_ERROR",
        "project.output-num": 3,
        "timeout.exploration": 240,
        "timeout.transform": 5,
        "timeout.hls": 20,
        "timeout.bitgen": 480,
        "evaluate.command.transform": "make mcc_acc",
        "evaluate.command.hls": "make mcc_estimate",
        "evaluate.command.bitgen": "make mcc_bitgen",
        "evaluate.estimate-mode": "FAST",
        "evaluate.worker-per-part": 2,
        "evaluate.max-util.BRAM": 0.8,
        "evaluate.max-util.DSP": 0.8,
        "evaluate.max-util.LUT": 0.8,
        "evaluate.max-util.FF": 0.8,
        "search.algorithm.name": "gradient",
        "search.algorithm.gradient.latency-threshold": 64,
        "search.algorithm.gradient.fine-grained-first": true,
        "search.algorithm.gradient.quality-type": "performance",
        "design-space.max-part-num": 4,
        "design-space-definition": {
            "K_PIPE": {
            "options": "['off','','flatten']",
            "order": "0 if x == 'flatten' else 1",
            "ds_type": "PIPELINE",
            "default": "off"
            },
            "K_PAR": {
            "options": "[x**2 for x in range(11)]",
            "ds_type": "PARALLEL",
            "default": 1
            },
            "I_PIPE": {
            "options": "[x for x in ['off','','flatten'] if x=='off' or K_PIPE!='flatten']",
            "order": "0 if x == 'flatten' else 1",
            "ds_type": "PIPELINE",
            "default": "off"
            },
            "I_PAR": {
            "options": "[x**2 for x in range(11) if x==0 or K_PIPE!='flatten']",
            "ds_type": "PARALLEL",
            "default": 1
            },
            "J_PIPE": {
            "options": "[x for x in ['off',''] if x=='off' or (K_PIPE!='flatten' and I_PIPE!='flatten')]",
            "ds_type": "PIPELINE",
            "default": "off"
            },
            "J_PAR": {
            "options": "[x**2 for x in range(11) if x==0 or (K_PIPE!='flatten' and I_PIPE!='flatten')]",
            "ds_type": "PARALLEL",
            "default": 1
            }
        }
    }

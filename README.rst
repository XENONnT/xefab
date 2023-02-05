=====
xefab
=====

Fabric based task execution for the XENON dark matter experiment


Installation
------------

To install xefab, its recomended to use pipx_:

.. code-block:: console

    $ pipx install xefab

Alternatively you can install it using pip:

.. code-block:: console

    $ pip install xefab

Usage
-----

You can list the available tasks using the ``--list`` option.

.. code-block:: console

    $ xefab --list
    
    Subcommands:

    echo
    dali.squeue            Get the job-queue status.
    dali.start-jupyter     Start a jupyter notebook on remote host.
    midway.squeue          Get the job-queue status.
    midway.start-jupyter   Start a jupyter notebook on remote host.
    osg.condor-q


    Remote Hosts:

    dali     dali-login2.rcc.uchicago.edu,dali-login1.rcc.uchicago.edu
    midway   midway2.rcc.uchicago.edu,midway1.rcc.uchicago.edu
    osg      login.xenon.ci-connect.net

Some tasks are registered to run on a specific host. When you run them, the --hosts option will be ignored.

e.g. if you run

.. code-block:: console

    $ xefab midway start-jupyter

The task will be run on the midway host, not the host you specified with --hosts.


Features
--------

* TODO

Credits
-------

This package was created with Cookiecutter_ and the `briggySmalls/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`briggySmalls/cookiecutter-pypackage`: https://github.com/briggySmalls/cookiecutter-pypackage
.. _pipx: https://github.com/pypa/pipx

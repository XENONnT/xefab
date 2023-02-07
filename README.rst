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

You can list the available tasks and options by running xefab without any options.

.. code-block:: console

    $ xefab
    Usage: xefab [--core-opts] <subcommand> [--subcommand-opts] ...

    Core options:

    --complete                         Print tab-completion candidates for given parse remainder.
    --hide=STRING                      Set default value of run()'s 'hide' kwarg.
    --print-completion-script=STRING   Print the tab-completion script for your preferred shell (bash|zsh|fish).
    --prompt-for-login-password        Request an upfront SSH-auth password prompt.
    --prompt-for-passphrase            Request an upfront SSH key passphrase prompt.
    --prompt-for-sudo-password         Prompt user at start of session for the sudo.password config value.
    --write-pyc                        Enable creation of .pyc files.
    -d, --debug                        Enable debug output.
    -D INT, --list-depth=INT           When listing tasks, only show the first INT levels.
    -e, --echo                         Echo executed commands before running.
    -f STRING, --config=STRING         Runtime configuration file to use.
    -F STRING, --list-format=STRING    Change the display format used when listing tasks. Should be one of: flat (default), nested,
                                        json.
    -h [STRING], --help[=STRING]       Show core or per-task help and exit.
    -H STRING, --hosts=STRING          Comma-separated host name(s) to execute tasks against.
    -i, --identity                     Path to runtime SSH identity (key) file. May be given multiple times.
    -l [STRING], --list[=STRING]       List available tasks, optionally limited to a namespace.
    -p, --pty                          Use a pty when executing shell commands.
    -R, --dry                          Echo commands instead of running.
    -S STRING, --ssh-config=STRING     Path to runtime SSH config file.
    -t INT, --connect-timeout=INT      Specifies default connection timeout, in seconds.
    -T INT, --command-timeout=INT      Specify a global command execution timeout, in seconds.
    -V, --version                      Show version and exit.
    -w, --warn-only                    Warn, instead of failing, when shell commands fail.

    Subcommands:

    show-config                        Get a config from the config server.
    admin.get-xenonnt-keys
    admin.github-cli
    admin.github-token
    admin.list-xenon1t-members
    admin.list-xenonnt-members
    admin.user-db
    dali.download-file                 Download a file from a remote server.
    dali.squeue (dali.job-queue)       Get the job-queue status.
    dali.start-jupyter                 Start a jupyter notebook on remote host.
    dali.submit-job                    Submit a job to the dali batch queue
    dali.upload-file                   Upload a file to a remote server.
    install.chezmoi
    install.github-cli
    install.gnupg
    install.go
    install.gopass
    midway.download-file               Download a file from a remote server.
    midway.squeue (midway.job-queue)   Get the job-queue status.
    midway.start-jupyter               Start a jupyter notebook on remote host.
    midway.submit-job                  Submit a job to the dali batch queue
    midway.upload-file                 Upload a file to a remote server.
    osg.condor-q (osg.job-queue)
    secrets.github-token
    secrets.setup
    secrets.setup-utilix-config


    Remote Hosts:

    dali     dali-login2.rcc.uchicago.edu,dali-login1.rcc.uchicago.edu
    midway   midway2.rcc.uchicago.edu,midway2-login1.rcc.uchicago.edu,midway2-login2.rcc.uchicago.edu
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

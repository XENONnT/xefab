=====
xefab
=====

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

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

You can list the available tasks and options by running xf/xefab without any options.

.. code-block:: console

    $ xf
    Usage: xf [--core-opts] [<host>] [<subcommand>] task1 [--task1-opts] ... taskN [--taskN-opts]

    Core options:

    --complete                      Print tab-completion candidates for given parse remainder.                                       
    --hide=STRING                   Set default value of run()'s 'hide' kwarg.                                                       
    --print-completion-script=STRINGPrint the tab-completion script for your preferred shell (bash|zsh|fish).                        
    --prompt-for-login-password     Request an upfront SSH-auth password prompt.                                                     
    --prompt-for-passphrase         Request an upfront SSH key passphrase prompt.                                                    
    --prompt-for-sudo-password      Prompt user at start of session for the sudo.password config value.                              
    --write-pyc                     Enable creation of .pyc files.                                                                   
    -d, --debug                     Enable debug output.                                                                             
    -D INT, --list-depth=INT        When listing tasks, only show the first INT levels.                                              
    -e, --echo                      Echo executed commands before running.                                                           
    -f STRING, --config=STRING      Runtime configuration file to use.                                                               
    -F STRING, --list-format=STRING Change the display format used when listing tasks. Should be one of: flat (default), nested,     
                                    json.                                                                                            
    -h [STRING], --help[=STRING]    Show core or per-task help and exit.                                                             
    -H STRING, --hosts=STRING       Comma-separated host name(s) to execute tasks against.                                           
    -i, --identity                  Path to runtime SSH identity (key) file. May be given multiple times.                            
    -l [STRING], --list[=STRING]    List available tasks, optionally limited to a namespace.                                         
    -p, --pty                       Use a pty when executing shell commands.                                                         
    -R, --dry                       Echo commands instead of running.                                                                
    -S STRING, --ssh-config=STRING  Path to runtime SSH config file.                                                                 
    -t INT, --connect-timeout=INT   Specifies default connection timeout, in seconds.                                                
    -T INT, --command-timeout=INT   Specify a global command execution timeout, in seconds.                                          
    -V, --version                   Show version and exit.                                                                           
    -w, --warn-only                 Warn, instead of failing, when shell commands fail.                                              


    Subcommands:

    show-context                      Show the context being used for tasks.                                                         
    admin.user-db                                                                                                                    
    dali.download-file                Download a file from a remote server.                                                          
    dali.sbatch                       Create and submit a job to SLURM job queue on the remote host.                                 
    dali.show-context                 Show the context being used for tasks.                                                         
    dali.squeue (dali.job-queue)      Get the job-queue status.                                                                      
    dali.start-jupyter                Start a jupyter analysis notebook on the remote host and forward to local port via ssh-tunnel. 
    dali.upload-file                  Upload a file to a remote server.                                                              
    github.clone                                                                                                                     
    github.is-private                                                                                                                
    github.is-public                                                                                                                 
    github.token                                                                                                                     
    github.xenon1t-members                                                                                                           
    github.xenonnt-keys                                                                                                              
    github.xenonnt-members                                                                                                           
    install.chezmoi                                                                                                                  
    install.get-system                                                                                                               
    install.github-cli (install.gh)                                                                                                  
    install.gnupg (install.gpg)                                                                                                      
    install.go                                                                                                                       
    install.gopass                                                                                                                   
    install.miniconda (install.conda)                                                                                                
    install.which                                                                                                                    
    midway.download-file              Download a file from a remote server.                                                          
    midway.sbatch                     Create and submit a job to SLURM job queue on the remote host.                                 
    midway.show-context               Show the context being used for tasks.                                                         
    midway.squeue (midway.job-queue)  Get the job-queue status.                                                                      
    midway.start-jupyter              Start a jupyter analysis notebook on the remote host and forward to local port via ssh-tunnel. 
    midway.upload-file                Upload a file to a remote server.                                                              
    osg.condorq (osg.job-queue)                                                                                                      
    osg.mc-chain                      Run a full chain MC simulation                                                                 
    secrets.setup                                                                                                                    
    secrets.setup-utilix-config                                                                                                      
    sh.exists                                                                                                                        
    sh.get-system                                                                                                                    
    sh.is-dir                                                                                                                        
    sh.is-file                                                                                                                       
    sh.path                                                                                                                          
    sh.shell (sh)                     Open interactive shell on remote host.                                                         
    sh.which                                                                   

You can get help for a specific task by running e.g.

.. code-block:: console

    $ xf --help midway.start-jupyter
    ╭─ start-jupyter ───────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
    │ xf [--core-opts] start-jupyter [--options][other tasks here ...]                                                              │
    │                                                                                                                               │
    │ Start a jupyter analysis notebook on the remote host and forward to local port via ssh-tunnel.                                │
    │                                                                                                                               │
    │ Options:                                                                                                                      │
    │ --image-dir=STRING                              Directory to look for singularity images                                      │
    │ --remote-port=STRING                            Port to use for jupyter server to on the worker node                          │
    │ --=INT, --local-port=INT                        Local port to attempt to forward to (if free)                                 │
    │ -a INT, --max-hours=INT                         Maximum number of hours to run for                                            │
    │ -b, --bypass-reservation                        Dont attempt to use the xenon notebook reservation                            │
    │ -c INT, --cpu=INT                               Number of CPUs to request                                                     │
    │ -d, --detached                                  Run the job and exit, dont perform cleanup tasks.                             │
    │ -e STRING, --env=STRING                         Environment to run on                                                         │
    │ -f, --force-new                                 Force a new job to be started                                                 │
    │ -g, --gpu                                       Use a GPU                                                                     │
    │ -i STRING, --binds=STRING                       Directories to bind to the container                                          │
    │ -j STRING, --jupyter=STRING                     Type of jupyter server to start (lab or notebook)                             │
    │ -l, --local-cutax                               Use user installed cutax (from ~/.local)                                      │
    │ -m INT, --timeout=INT                           Timeout for the job to start                                                  │
    │ -n STRING, --node=STRING                        Node to run on                                                                │
    │ -o STRING, --notebook-dir=STRING                Directory to start the notebook in                                            │
    │ -p STRING, --partition=STRING                   Partition to run on (xenon1t or dali)                                         │
    │ -r INT, --ram=INT                               Amount of RAM to allocate (in MB)                                             │
    │ -t STRING, --tag=STRING                         Tag of the container to use                                                   │
    │ -u, --debug                                     Print debug information                                                       │
    │ -w, --no-browser                                Dont open the browser automatically when done                                 │
    ╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Some tasks are registered to run on a specific host. When you run them, the --hosts option will be ignored.

e.g. if you run

.. code-block:: console

    $ xf midway start-jupyter

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

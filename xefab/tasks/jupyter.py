import json
import random
import time
from io import BytesIO, StringIO
from random import choices
from string import ascii_lowercase

from fabric.tasks import task
from rich.progress import SpinnerColumn, TextColumn
from rich.prompt import IntPrompt
from xefab.tasks.shell import is_file

from xefab.utils import ProgressContext, console, get_open_port

from .squeue import parse_squeue_output, squeue
from .utils import print_splash

JOB_NAME = "xefab-jupyter"


JOB_HEADER = """#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --output={log_fn}
#SBATCH --error={log_fn}
#SBATCH --account=pi-lgrandi
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={n_cpu}
#SBATCH --mem-per-cpu={mem_per_cpu}
#SBATCH --time={max_hours}:00:00
{extra_header}

export NUMEXPR_MAX_THREADS={n_cpu}


"""

GPU_HEADER = """\
#SBATCH --partition=gpu2
#SBATCH --gres=gpu:1

module load cuda/10.1
"""

CPU_HEADER = """\
#SBATCH --qos {qos}
#SBATCH --partition {partition}
{reservation}
"""


# This is only if the user is NOT starting the singularity container
# (for singularity, starting jupyter is done in _xentenv_inner)
START_JUPYTER = """
echo $PYTHONPATH
echo Starting jupyter job

jupyter {jupyter} --no-browser --port={port} --ip=0.0.0.0 --notebook-dir {notebook_dir} 2>&1
"""


START_JUPYTER_SINGULARITY = """
SINGULARITY_CACHEDIR=$TMPDIR/singularity_cache

mkdir -p $SINGULARITY_CACHEDIR

# SINGULARITY_CACHEDIR=/home/{user}/scratch/singularity_cache
echo Loading singularity module

module load singularity

echo Starting jupyter job

singularity exec {bind_str} {container} jupyter {jupyter} --no-browser --port={port} --ip=0.0.0.0 

"""
# --notebook-dir {notebook_dir}

@task(
    pre=[print_splash],
    help={
        "env": "Environment to run on",
        "partition": "Partition to run on (xenon1t or dali)",
        "bypass_reservation": "Dont attempt to use the xenon notebook reservation",
        "tag": "Tag of the container to use",
        "binds": "Directories to bind to the container",
        "node": "Node to run on",
        "timeout": "Timeout for the job to start",
        "cpu": "Number of CPUs to request",
        "ram": "Amount of RAM to allocate (in MB)",
        "gpu": "Use a GPU",
        "jupyter": "Type of jupyter server to start (lab or notebook)",
        "local_cutax": "Use user installed cutax (from ~/.local)",
        "notebook_dir": "Directory to start the notebook in",
        "max_hours": "Maximum number of hours to run for",
        "force_new": "Force a new job to be started",
        "local_port": "Local port to attempt to forward to (if free)",
        "remote_port": "Port to use for jupyter server to on the worker node",
        "detached": "Run the job and exit, dont perform cleanup tasks.",
        "no_browser": "Dont open the browser automatically when done",
        "image_dir": "Directory to look for singularity images",
        "debug": "Print debug information",
    },
)
def start_jupyter(
    c,
    env: str = "singularity",
    partition: str = None,
    bypass_reservation: bool = False,
    tag: str = "development",
    binds: str = None,
    node: str = None,
    timeout: int = 120,
    cpu: int = 2,
    ram: int = 8000,
    gpu: bool = False,
    jupyter: str = "lab",
    local_cutax: bool = False,
    notebook_dir: str = None,
    max_hours: int = 4,
    force_new: bool = False,
    local_port: int = 8888,
    remote_port: int = None,
    detached: bool = False,
    no_browser: bool = False,
    image_dir: str = None,
    debug: bool = False,
):
    """Start a jupyter analysis notebook on the remote \
host and forward to local port via ssh-tunnel."""

    REMOTE_HOME = f"/home/{c.user}"

    if image_dir is None:
        image_dir = "/project2/lgrandi/xenonnt/singularity-images"

    if notebook_dir is None:
        notebook_dir = REMOTE_HOME

    if remote_port is None:
        remote_port = random.randrange(15000, 20000)

    if partition is None:
        partition = "dali" if c.original_host == "dali" else "xenon1t"

    # bind directories inside the container
    if binds is None:
        binds = f"/project2,/scratch/midway2/{c.user},/dali"
    if isinstance(binds, str):
        binds = [bind.strip() for bind in binds.split(",")]
    
    if partition == "xenon1t":
        binds.append("/project2/lgrandi/xenonnt/dali/lgrandi/xenonnt/software/cutax:/xenon/xenonnt/software/cutax")

    bind_str = " ".join([f"--bind {bind}" for bind in binds])

    console.print(f"Using partition {partition}")

    local_port = get_open_port(start=local_port)
    env_vars = {}

    if local_cutax:
        console.print(
            "Container cutax being overwritten by user installed package.",
            style="warning",
        )
        env_vars["INSTALL_CUTAX"] = "0"

    
    if not force_new:
        with ProgressContext() as progress:
            existing_jobs = {}
            with progress.enter_task("Checking for existing jobs") as task:
                # Check for existing jobs
                existing_jobs = get_existing_jobs(c)

                if existing_jobs:
                    progress.update(task, description="Found existing jobs.")
                else:
                    progress.update(task, description="No existing jobs found.")

        if existing_jobs:
            console.print("Found existing jobs, options:")
            progress.console.print(f"(0): Start new job",)
            jobnames = list(existing_jobs)
            for i, job_name in enumerate(jobnames):
                console.print(
                    f"({i+1}): {job_name}", 
                )
            
            selection = IntPrompt.ask(
                "Select a job to connect to or start new job",
                choices=list(map(str,range(0, len(jobnames) + 1))),
                console=progress.console, default='0',
            )
    

            if selection < len(jobnames) + 1:
                job_name = jobnames[selection - 1]
                server_details = existing_jobs[job_name]
                job_folder = f"{REMOTE_HOME}/xefab_jobs/{job_name}"

                with ProgressContext() as progress:
                    attach_to_job(c, job_id=server_details['job_id'], local_port=local_port, 
                                remote_host=server_details['remote_host'],
                                remote_port=server_details['remote_port'], 
                                token=server_details['token'], progress=progress,
                                job_folder=job_folder, no_browser=no_browser, 
                                detached=detached, debug=debug)
                    return

    with ProgressContext() as progress:
        unique_id = "".join(choices(ascii_lowercase, k=4))
        date = time.strftime("%Y%m%d")

        job_name = f"jupyter_{unique_id}_{date}" 
        job_folder = f"{REMOTE_HOME}/xefab_jobs/{job_name}"

        server_details_path = f"{job_folder}/server_details.json"

        with progress.enter_task("Checking connection and destination folder"):
            if not c.run(f"test -d {job_folder}", warn=True).ok:
                progress.console.print(f"Creating {job_folder} on {c.host}")
                c.run("mkdir -p " + job_folder)

        if env == "singularity":
            s_container = f"/cvmfs/singularity.opensciencegrid.org/xenonnt/base-environment:{tag}"
            # s_container = f"{image_dir}/xenonnt-{tag}.simg"

            # Add the singularity runner script to the batch job
            # batch_job = JOB_HEADER + f"{starter_path} "
            batch_job = JOB_HEADER + START_JUPYTER_SINGULARITY.format(
                user=c.user,
                bind_str=bind_str,
                container=s_container,
                jupyter=jupyter,
                notebook_dir=notebook_dir,
                port=remote_port,
            )

        elif env == "cvmfs":
            batch_job = (
                JOB_HEADER
                + "source /cvmfs/xenon.opensciencegrid.org/releases/nT/%s/setup.sh"
                % (tag)
                + START_JUPYTER.format(
                    jupyter=jupyter, notebook_dir=notebook_dir, port=remote_port
                )
            )
            console.print(
                "Using conda from cvmfs (%s) instead of singularity container." % (tag),
                style="info",
            )

        elif env == "backup":
            if tag != "development":
                raise ValueError(
                    "I'm going to give you the latest container, you cannot choose a version!"
                )
            batch_job = (
                JOB_HEADER
                + "source /dali/lgrandi/strax/miniconda3/bin/activate strax"
                + START_JUPYTER.format(
                    jupyter=jupyter, notebook_dir=notebook_dir, port=remote_port
                )
            )
            console.print(
                "Using conda from cvmfs (%s) instead of singularity container." % (tag)
            )

        if partition == "kicp":
            qos = "xenon1t-kicp"
        else:
            qos = partition

        # FIXME: check if a job is already running.

        _want_to_make_reservation = partition == "xenon1t" and (not bypass_reservation)
        if ram > 16000 and _want_to_make_reservation:
            console.print(
                "You asked for more than 16 GB total memory you cannot use the notebook "
                "reservation queue for this job! We will bypass the reservation."
            )

        if cpu >= 8 and _want_to_make_reservation:
            console.print(
                "You asked for more than 7 CPUs you cannot use the notebook reservation "
                "queue for this job! We will bypass the reservation."
            )
        use_reservation = (
            (not force_new) and _want_to_make_reservation and cpu < 8 and ram <= 16000
        )

        if use_reservation:
            with progress.enter_task(
                "Notebook reservation requested. Checking availability",
                finished_description="using Notebook reservation.",
                exception_description="Notebook reservation does not exist, submitting a regular job.",
                warn=True,
                hide=not debug,
            ):
                result = c.run("scontrol show reservations", hide=True, warn=True)
                if (
                    result.failed
                    or "ReservationName=xenon_notebook" not in result.stdout
                ):
                    use_reservation = False
                    raise RuntimeError("Notebook reservation does not exist.")

        # with progress.enter_task("Checking for existing jobs"):
        #     result = c.run(f"squeue -u {c.user} -n straxlab", hide=True, warn=True)
        #     df = parse_squeue_output(result.stdout)
        job_fn = "/".join([job_folder, "notebook.sbatch"])
        log_fn = "/".join([job_folder, "notebook.log"])

        extra_header = (
            GPU_HEADER
            if gpu
            else CPU_HEADER.format(
                partition=partition,
                qos=qos,
                reservation=(
                    "#SBATCH --reservation=xenon_notebook" if use_reservation else ""
                ),
            )
        )

        if node:
            extra_header += "\n#SBATCH --nodelist={node}".format(node=node)
        if max_hours is None:
            max_hours = 2 if gpu else 8
        else:
            max_hours = int(max_hours)

        batch_job = batch_job.format(
            job_name=job_name,
            log_fn=log_fn,
            max_hours=max_hours,
            extra_header=extra_header,
            n_cpu=cpu,
            mem_per_cpu=int(ram / cpu),
        )

        with progress.enter_task("Reseting log file"):
            c.put(StringIO(""), remote=log_fn)

        with progress.enter_task("Copying batch job to remote host"):
            c.put(StringIO(batch_job), remote=job_fn)

        with progress.enter_task("Setting permissions on batch job"):
            c.run("chmod +x " + job_fn)

        with progress.enter_task("Submitting batch job"):
            result = c.run("sbatch " + job_fn, env=env_vars, hide=True, warn=True)

        if result.failed:
            raise RuntimeError("Could not submit batch job. Error: " + result.stderr)

        job_id = int(result.stdout.split()[-1])

        console.print("Submitted job with ID: %d" % job_id)

        with progress.enter_task(
            "Waiting for your job to start",
            finished_description="Job started.",
            exception_description="Job did not start.",
        ):
            for _ in range(timeout):
                result = c.run("squeue -j %d" % job_id, hide=True, warn=True)
                df = parse_squeue_output(result.stdout)
                if len(df) and df["ST"].iloc[0] == "R":
                    break
                elif len(df) and df["ST"].iloc[0] == "C":
                    raise RuntimeError("Job was cancelled.")
                time.sleep(1)
            else:
                raise RuntimeError("Timeout reached while waiting for job to start.")

        with progress.enter_task(
            "Waiting for jupyter server to start",
            finished_description="Jupyter server started.",
            exception_description="Jupyter server did not start.",
        ):
            url = None
            for _ in range(timeout):
                time.sleep(1)
                log_content = BytesIO()
                result = c.get(log_fn, local=log_content)
                log_content.seek(0)
                lines = [line.decode() for line in log_content.readlines()]

                for line in lines:
                    if "http://" in line and f":{remote_port}" in line:
                        url = line.split()[-1]
                        break
                else:
                    result = c.run("squeue -j %d" % job_id, hide=True, warn=True)
                    df = parse_squeue_output(result.stdout)
                    if not len(df):
                        raise RuntimeError(
                            "Job has exited."
                            "This can be because it was canceled or due to an internal error."
                        )
                    continue
                break
            else:
                raise RuntimeError(
                    "Timeout reached while waiting for jupyter to start."
                )

            console.print("\nJupyter started succesfully.")
            console.print(f"Remote URL: \n{url}\n")
            remote_host, remote_port = url.split("/")[2].split(":")
            if "token" in url:
                token = url.split("?")[1].split("=")[1]
            else:
                token = ""

        # Can never be too careful, make sure port numbers are integers
        local_port = int(local_port)
        remote_port = int(remote_port)

        server_details = {
            "job_id": job_id,
            "job_name": job_name,
            "remote_host": remote_host,
            "remote_port": remote_port,
            "token": token,
        }

        # Persist server details
        with progress.enter_task(
            "Writing server details to file",
            finished_description="Server details saved",
            warn=True,
        ):
            details_fd = StringIO(json.dumps(server_details, indent=4))
            c.put(details_fd, remote=server_details_path)

        attach_to_job(c, job_id=job_id, local_port=local_port, remote_host=remote_host,
            remote_port=remote_port, token=token, progress=progress, job_folder=job_folder,
            no_browser=no_browser, detached=detached, debug=debug)

def attach_to_job(c, *, job_id, local_port, remote_host, 
            remote_port, token, progress, job_folder,
            no_browser=False, detached=False, debug=False):
    """Attach to a running job."""

        # Handle port forwarding
    if token:
        local_url = f"http://localhost:{local_port}?token={token}"
    else:
        local_url = f"http://localhost:{local_port}"
    msg = f"Forwarding remote address {remote_host}:{remote_port} to local port {local_port}"
    if not detached:
        extra_msg = (
            f"\nYou can access the notebook at \n{local_url}\n"
            "   Press ENTER or CTRL-C to deactivate and cancel job."
        )
        with progress.enter_task(
            msg + extra_msg,
            exception_description="Exception raised while forwarding port",
            warn=True,
        ) as task:
            with c.forward_local(
                local_port, remote_port=remote_port, remote_host=remote_host
            ):
                time.sleep(3)

                if not no_browser:
                    result = c.local(
                        f"python -m webbrowser -t {local_url}", hide=True, warn=True
                    )
                try:
                    r = progress.console.input()
                    progress.update(
                        task, description="Deactivating port forwarding"
                    )
                    time.sleep(2)
                except KeyboardInterrupt:
                    console.print("Keyboard interrupt received.")
                except Exception as e:
                    if debug:
                        console.print(f"Exception raised: {e}")
                    else:
                        console.print(f"Exception raised.")

        with progress.enter_task(
            "Canceling job",
            finished_description="Job canceled",
            exception_description=f"Could not cancel job. Please cancel it manually. Job ID: {job_id}",
            warn=True,
        ):
            c.run(f"scancel {job_id}", hide=True)

        if not debug:
            with progress.enter_task(
                "Cleaning up job files",
                finished_description="Job folder removed",
                exception_description=f"Could not remove job folder. Please remove it manually. Path: {job_folder}",
            ):
                for _ in range(3):
                    time.sleep(2)
                    result = c.run(f"rm -rf {job_folder}", hide=True, warn=True)
                    if result.ok:
                        break
                else:
                    raise

    else:
        # Detached mode - just forward the port and exit
        with progress.enter_task(msg, warn=True) as task:
            result = c.local(
                f"ssh -fN -L {local_port}:{remote_host}:{remote_port} {c.user}@{c.host} &",
                disown=True,
                hide=False,
                warn=True,
            )
            time.sleep(3)
            console.print(f"You can access the notebook at \n{local_url}\n")
            if result.ok and not no_browser:
                c.local(
                    f"python -m webbrowser -t {local_url}", hide=True, warn=True
                )

    console.print("Goodbye!")


def get_existing_jobs(c):
    """Find all running jupyter jobs on the remote host."""
    df = squeue(c, hide=True)
    running = {}
    for job_name in df["NAME"]:
        details_path = f"/home/{c.user}/xefab_jobs/{job_name}/server_details.json"
        if job_name.startswith('jupyter') and is_file(c, details_path, hide=True):
            running[job_name] = json.loads(c.run(f"cat {details_path}", hide=True).stdout)
    return running

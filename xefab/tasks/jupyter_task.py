import json
import random
import time
import webbrowser
from io import BytesIO, StringIO
from random import choices
from string import ascii_lowercase

from fabric.tasks import task
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn

from xefab.utils import console, get_open_port, ProgressContext

from .squeue_task import parse_squeue_output
from .utils import print_splash

JOB_NAME = 'xefab-jupyter'

PROGRESS_COLUMNS = [
    SpinnerColumn(finished_text="[bold green]✓[/bold green]"),
    TextColumn("{task.description}"),
    SpinnerColumn(spinner_name="simpleDots", finished_text=""),
]


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
echo Starting jupyter job

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
jupyter {jupyter} --no-browser --port={port} --ip=0.0.0.0 --notebook-dir {notebook_dir} 2>&1
"""


START_NOTEBOOK_SH = """
#!/bin/bash

echo "Using singularity image: {CONTAINER}"

SINGULARITY_CACHEDIR=/scratch/midway2/{USER}/singularity_cache

module load singularity

singularity exec {BIND_STR} {CONTAINER} jupyter {JUPYTER_TYPE} --no-browser --port={PORT} --ip=0.0.0.0 --notebook-dir {NOTEBOOK_DIR}

"""


@task(pre=[print_splash])
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
    """Start a jupyter notebook on remote host."""

    REMOTE_HOME = f"/home/{c.user}"

    unique_id = "".join(choices(ascii_lowercase, k=4))
    date = time.strftime("%Y%m%d")

    job_name = f"jupyter_{unique_id}_{date}"
    job_folder = f"{REMOTE_HOME}/xefab_jobs/{job_name}"

    server_details_path = f"{job_folder}/server_details.json"

    if image_dir is None:
        image_dir = "/project2/lgrandi/xenonnt/singularity-images"

    if notebook_dir is None:
        notebook_dir = REMOTE_HOME

    if remote_port is None:
        remote_port = random.randrange(15000, 20000)

    if partition is None:
        partition = "dali" if c.original_host == "dali" else "xenon1t"

    if binds is None:
        binds = "/project2,/scratch,/dali"
    if isinstance(binds, str):
        binds = [bind.strip() for bind in binds.split(",")]
    bind_str = " ".join([f"--bind {bind}" for bind in binds])

    console.print(f"Using partition {partition}", style="info")

    local_port = get_open_port(start=local_port)
    env_vars = {}

    if local_cutax:
        console.warn(
            "Container cutax being overwritten by user installed package.",
            style="warning",
        )
        env_vars["INSTALL_CUTAX"] = "0"

    with ProgressContext(*PROGRESS_COLUMNS) as progress:
        with progress.enter_task("Checking connection and destination folder"):
            if not c.run(f"test -d {job_folder}", warn=True).ok:
                progress.console.print(f"Creating {job_folder} on {c.host}")
                c.run("mkdir -p " + job_folder)

        if env == "singularity":
            with progress.enter_task("Building singularity runner script"):
                s_container = f"{image_dir}/xenonnt-{tag}.simg"
                starter_path = f"{job_folder}/start_notebook.sh"
                starter_script = START_NOTEBOOK_SH.format(
                    CONTAINER=s_container,
                    JUPYTER_TYPE=jupyter,
                    NOTEBOOK_DIR=notebook_dir,
                    PORT=remote_port,
                    BIND_STR=bind_str,
                    USER=c.user,
                )

            # Add the singularity runner script to the batch job
            batch_job = JOB_HEADER + f"{starter_path} "

            with progress.enter_task("Uploading singularity runner script",
                finished_description="Singularity runner script uploaded",) as task:
                starter_script_fd = StringIO(starter_script)
                c.put(starter_script_fd, remote=starter_path)
                progress.update(task, description="Making script executable")
                c.run(f"chmod +x {starter_path}")

        elif env == "cvmfs":
            batch_job = (
                JOB_HEADER
                + "source /cvmfs/xenon.opensciencegrid.org/releases/nT/%s/setup.sh"
                % (tag)
                + START_JUPYTER.format(jupyter=jupyter, notebook_dir=notebook_dir, port=remote_port)
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
                + START_JUPYTER.format(jupyter=jupyter, notebook_dir=notebook_dir, port=remote_port)
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
                raise_exceptions=False):
                result = c.run("scontrol show reservations", hide=True, warn=True)
                if result.failed or "ReservationName=xenon_notebook" not in result.stdout:
                    use_reservation = False
                    raise

        with progress.enter_task("Checking for existing jobs"):
            result = c.run(f"squeue -u {c.user} -n straxlab", hide=True, warn=True)
            df = parse_squeue_output(result.stdout)
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

        with progress.enter_task("Waiting for your job to start",
                            finished_description="Job started.",
                            exception_description="Job did not start."):
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

        with progress.enter_task("Waiting for jupyter server to start",
                                 finished_description="Jupyter server started.",
                                 exception_description="Jupyter server did not start."):
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
                raise RuntimeError("Timeout reached while waiting for jupyter to start.")

            console.print("\nJupyter started succesfully.")
            console.print(f"Remote URL: \n{url}\n")
            remote_host, remote_port = url.split("/")[2].split(":")
            if "token" in url:
                token = url.split("?")[1].split("=")[1]
                local_url = f"http://localhost:{local_port}?token={token}"
            else:
                token = ""
                local_url = f"http://localhost:{local_port}"

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
        with progress.enter_task("Writing server details to file",
                                 finished_description="Server details saved",
                                 raise_exceptions=False):
            details_fd = StringIO(json.dumps(server_details))
            c.put(details_fd, remote=server_details_path)

        # Handle port forwarding
        msg = f"Forwarding remote address {remote_host}:{remote_port} to local port {local_port}"
        if not detached:
            extra_msg =(f"\nYou can access the notebook at \n{local_url}\n"
                        "   Press ENTER or CTRL-C to deactivate and cancel job."
                    )
            with progress.enter_task(msg+extra_msg,
                        exception_description="Exception raised while forwarding port",
                        raise_exceptions=False) as task:
               
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
                        progress.update(task, description="Deactivating port forwarding")
                        time.sleep(2)
                    except KeyboardInterrupt:
                        console.print("Keyboard interrupt received.")
                    except Exception as e:
                        if debug:
                            console.print(f"Exception raised: {e}")
                        else:
                            console.print(f"Exception raised.")
        
            with progress.enter_task("Canceling job",
                finished_description="Job canceled",
                exception_description=f"Could not cancel job. Please cancel it manually. Job ID: {job_id}",
                raise_exceptions=False):
                c.run(f"scancel {job_id}", hide=True)

            if not debug:
                with progress.enter_task("Cleaning up job files",
                    finished_description="Job folder removed",
                    exception_description=f"Could not remove job folder. Please remove it manually. Path: {job_folder}",):
                    for _ in range(3):
                        time.sleep(2)
                        result = c.run(f"rm -rf {job_folder}", hide=True, warn=True)
                        if result.ok:
                            break
                    else:
                        raise

        else:
            # Detached mode - just forward the port and exit
            with progress.enter_task(msg, raise_exceptions=False) as task:

                result = c.local(
                    f"ssh -fN -L {local_port}:{remote_host}:{remote_port} {c.user}@{c.host} &",
                    disown=True,
                    hide=False,
                    warn=True,
                )
                time.sleep(3)
                console.print(f"You can access the notebook at \n{local_url}\n")
                if result.ok and not no_browser:
                    c.local(f"python -m webbrowser -t {local_url}", hide=True, warn=True)
                
    console.print("Goodbye!")

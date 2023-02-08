import random
import time
import webbrowser
from io import BytesIO, StringIO
from random import choices
from string import ascii_lowercase

from fabric.tasks import task
from rich.layout import Layout
from rich.panel import Panel

from xefab.utils import console, get_open_port

from .squeue_task import parse_squeue_output
from .utils import print_splash


SPLASH_SCREEN = r"""
 __   __ ______  _   _   ____   _   _      _______ 
 \ \ / /|  ____|| \ | | / __ \ | \ | |    |__   __|
  \ V / | |__   |  \| || |  | ||  \| | _ __  | |   
   > <  |  __|  | . ` || |  | || . ` || '_ \ | |   
  / . \ | |____ | |\  || |__| || |\  || | | || |   
 /_/ \_\|______||_| \_| \____/ |_| \_||_| |_||_|   

                    The UChicago Analysis Center

"""

JOB_HEADER = """#!/bin/bash
#SBATCH --job-name=straxlab
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
JUP_PORT=$(( 15000 + (RANDOM %= 5000) ))
JUP_HOST=$(hostname -i)
echo $PYTHONPATH
jupyter {jupyter} --no-browser --port=$JUP_PORT --ip=$JUP_HOST --notebook-dir {notebook_dir} 2>&1
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

    print = console.print

    unique_id = "".join(choices(ascii_lowercase, k=6))

    if image_dir is None:
        image_dir = "/project2/lgrandi/xenonnt/singularity-images"

    REMOTE_HOME = f"/home/{c.user}"
    if notebook_dir is None:
        notebook_dir = REMOTE_HOME
    output_folder = f"{REMOTE_HOME}/straxlab"

    if remote_port is None:
        remote_port = random.randrange(15000, 20000)

    if partition is None:
        partition = "dali" if c.original_host == "dali" else "xenon1t"

    if binds is None:
        binds = "/project2, /scratch, /dali"

    if isinstance(binds, str):
        binds = [bind.strip() for bind in binds.split(",")]

    bind_str = " ".join([f"--bind {bind}" for bind in binds])

    print(f"Using partition {partition}")

    local_port = get_open_port(start=local_port)
    env_vars = {}

    if local_cutax:
        env_vars["INSTALL_CUTAX"] = "0"

    with console.status("Checking if job folder exists...") as status:
        if not c.run(f"test -d {output_folder}", warn=True).ok:
            status.update("Creating job folder...")
            c.run("mkdir -p " + output_folder)

    if env == "singularity":
        s_container = f"{image_dir}/xenonnt-{tag}.simg"
        starter_path = f"{output_folder}/start_notebook_{unique_id}.sh"
        starter_script = START_NOTEBOOK_SH.format(
            CONTAINER=s_container,
            JUPYTER_TYPE=jupyter,
            NOTEBOOK_DIR=notebook_dir,
            PORT=remote_port,
            BIND_STR=bind_str,
            USER=c.user,
        )
        starter_script_fd = StringIO(starter_script)
        with console.status(f"Copying starter script to {c.host}:{starter_path} ..."):
            c.put(starter_script_fd, remote=starter_path)

        with console.status("Making starter script executable..."):
            c.run(f"chmod +x {starter_path}")

        batch_job = JOB_HEADER + f"{starter_path} "

    elif env == "cvmfs":
        batch_job = (
            JOB_HEADER
            + "source /cvmfs/xenon.opensciencegrid.org/releases/nT/%s/setup.sh" % (tag)
            + START_JUPYTER.format(jupyter=jupyter, notebook_dir=notebook_dir)
        )
        print("Using conda from cvmfs (%s) instead of singularity container." % (tag))

    elif env == "backup":
        if tag != "development":
            raise ValueError(
                "I'm going to give you the latest container, you cannot choose a version!"
            )
        batch_job = (
            JOB_HEADER
            + "source /dali/lgrandi/strax/miniconda3/bin/activate strax"
            + START_JUPYTER.format(jupyter=jupyter, notebook_dir=notebook_dir)
        )
        print("Using conda from cvmfs (%s) instead of singularity container." % (tag))

    if partition == "kicp":
        qos = "xenon1t-kicp"
    else:
        qos = partition

    # FIXME: check if a job is already running.

    _want_to_make_reservation = partition == "xenon1t" and (not bypass_reservation)
    if ram > 16000 and _want_to_make_reservation:
        print(
            "You asked for more than 16 GB total memory you cannot use the notebook "
            "reservation queue for this job! We will bypass the reservation."
        )

    if cpu >= 8 and _want_to_make_reservation:
        print(
            "You asked for more than 7 CPUs you cannot use the notebook reservation "
            "queue for this job! We will bypass the reservation."
        )
    use_reservation = (
        (not force_new) and _want_to_make_reservation and cpu < 8 and ram <= 16000
    )

    if use_reservation:
        with console.status("Notebook reservation requested. Checking availability..."):
            result = c.run("scontrol show reservations", hide=True, warn=True)
            if result.failed or "ReservationName=xenon_notebook" not in result.stdout:
                print("Notebook reservation does not exist, submitting a regular job.")
                use_reservation = False

    with console.status("Checking for existing jobs..."):
        result = c.run(f"squeue -u {c.user} -n straxlab", hide=True, warn=True)
        df = parse_squeue_output(result.stdout)
        if len(df) or force_new:
            job_fn = "/".join([output_folder, f"notebook_{unique_id}.sbatch"])
            log_fn = "/".join([output_folder, f"notebook_{unique_id}.log"])
        else:
            job_fn = "/".join([output_folder, "notebook.sbatch"])
            log_fn = "/".join([output_folder, "notebook.log"])

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
        log_fn=log_fn,
        max_hours=max_hours,
        extra_header=extra_header,
        n_cpu=cpu,
        mem_per_cpu=int(ram / cpu),
    )

    with console.status("Reseting log file..."):
        c.put(StringIO(""), remote=log_fn)

    with console.status("Copying batch job to remote host..."):
        c.put(StringIO(batch_job), remote=job_fn)

    with console.status("Setting permissions on batch job..."):
        c.run("chmod +x " + job_fn)

    with console.status("Submitting batch job..."):
        result = c.run("sbatch " + job_fn, env=env_vars, hide=True, warn=True)

    if result.failed:
        raise RuntimeError("Could not submit batch job. Error: " + result.stderr)

    job_id = int(result.stdout.split()[-1])

    print("Submitted job with ID: %d" % job_id)

    with console.status("Waiting for your job to start..."):
        for _ in range(timeout):
            result = c.run("squeue -j %d" % job_id, hide=True, warn=True)
            df = parse_squeue_output(result.stdout)
            if len(df) and df["ST"].iloc[0] == "R":
                break
            time.sleep(1)
        else:
            raise RuntimeError("Timeout reached while waiting for job to start.")

    print("Job started.")

    with console.status("Waiting for jupyter server to start...") as status:
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

        print("\nJupyter started succesfully.")
        print(f"Remote URL: \n{url}\n")
        remote_host, remote_port = url.split("/")[2].split(":")
        if "token" in url:
            token = url.split("?")[1].split("=")[1]
            local_url = f"http://localhost:{local_port}?token={token}"
        else:
            token = ""
            local_url = f"http://localhost:{local_port}"

    msg = f"Forwarding remote address {remote_host}:{remote_port} to local port {local_port}..."
    with console.status(msg) as status:
        print(f"You can access the notebook at \n{local_url}\n")

        if detached:
            c.local(
                f"ssh -fN -L {local_port}:{remote_host}:{remote_port} {c.user}@{c.host} &",
                disown=True,
                hide=False,
                warn=True,
            )
            time.sleep(3)
            if not no_browser:
                c.local(f"python -m webbrowser -t {local_url}", hide=True, warn=True)
        else:
            # Can never be too careful
            local_port = int(local_port)
            remote_port = int(remote_port)
            with c.forward_local(
                local_port, remote_port=remote_port, remote_host=remote_host
            ):
                status.update(
                    "Local port forwarding is active.\n"
                    "   Press ENTER or CTRL-C to deactivate and cancel job."
                )
                time.sleep(3)
                if not no_browser:
                    result = c.local(
                        f"python -m webbrowser -t {local_url}", hide=True, warn=True
                    )
                try:
                    console.input()
                except KeyboardInterrupt:
                    print("Keyboard interrupt received.")
                except:
                    print("Unknown error.")
                finally:
                    status.update("Closing tunnel and canceling job...")
            try:
                c.run("scancel %d" % job_id, hide=True)
            except:
                print("Could not cancel job. Please cancel it manually.")
            finally:
                if not debug:
                    status.update("Cleaning up job files...")
                    result = c.run("rm %s" % job_fn, hide=True, warn=True)
                    if result.failed:
                        print("Could not remove job batch file.")
                    else:
                        print("Job batch file removed.")
                    result = c.run("rm %s" % log_fn, hide=True, warn=True)
                    if result.failed:
                        print("Could not remove log file.")
                    else:
                        print("Log file removed.")
                    for _ in range(3):
                        time.sleep(2)
                        result = c.run("rm %s" % starter_path, hide=True, warn=True)
                        if result.ok:
                            print("job executable file removed.")
                            break
                    else:
                        print(
                            "Could not job executable. Please remove it manually. Path: {starter_path}"
                        )

    print("Goodbye!")

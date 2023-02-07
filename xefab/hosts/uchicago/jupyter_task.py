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


SUCCESS_MESSAGE = """
All done! If you have linux, execute this command on your laptop:

ssh -fN -L {port}:{ip}:{port} {username}@{host} && sensible-browser http://localhost:{port}/{token}

If you have a mac, instead do:

ssh -fN -L {port}:{ip}:{port} {username}@{host} && open "http://localhost:{port}/{token}"

Happy strax analysis, {username}!
"""


START_NOTEBOOK_SH = """
#!/bin/bash

IMAGE_NAME=$1
JUPYTER_TYPE=$2
NOTEBOOK_DIR=$3

IMAGE_DIR='/project2/lgrandi/xenonnt/singularity-images'

# if we passed the full path to an image, use that
if [ -e ${IMAGE_NAME} ]; then
  CONTAINER=${IMAGE_NAME}
# otherwise check if the name exists in the standard image directory
elif [ -e ${IMAGE_DIR}/${IMAGE_NAME} ]; then
  CONTAINER=${IMAGE_DIR}/${IMAGE_NAME}
# if not any of those, throw an error
else
  echo "We could not find the container at its full path ${IMAGE_NAME} or in ${IMAGE_DIR}. Exiting."
  exit 1
fi

if [ "x${JUPYTER_TYPE}" = "x" ]; then
  JUPYTER_TYPE='lab'
fi

echo "Using singularity image: ${CONTAINER}"

PORT=$(( 15000 + (RANDOM %= 5000) ))
SINGULARITY_CACHEDIR=/scratch/midway2/$USER/singularity_cache

# script to run inside container
INNER=/home/$USER/straxlab/.singularity_inner_${PORT}.sh
cat > $INNER << EOF
#!/bin/bash
JUP_HOST=\$(hostname -i)
## print tunneling instructions
echo -e "
    Copy/Paste this in your local terminal to ssh tunnel with remote
    -----------------------------------------------------------------
    ssh -N -f -L localhost:$PORT:\$JUP_HOST:$PORT ${USER}@midway2.rcc.uchicago.edu
    -----------------------------------------------------------------

    Then open a browser on your local machine to the following address
    ------------------------------------------------------------------
    localhost:$PORT
    ------------------------------------------------------------------
    and use the token that appears below to login.

    OR replace "$ipnip" in the address below with "localhost" and copy
    to your local browser.
    " 2>&1

jupyter ${JUPYTER_TYPE} --no-browser --port=$PORT --ip=\$JUP_HOST --notebook-dir ${NOTEBOOK_DIR} 2>&1
EOF
chmod +x $INNER

module load singularity
singularity exec --bind /project2 --bind /scratch/midway2/$USER --bind /dali $CONTAINER $INNER

"""


@task(pre=[print_splash])
def start_jupyter(
    c,
    env: str = "singularity",
    partition: str = "xenon1t",
    bypass_reservation: bool = False,
    tag: str = "development",
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
    local_port=8889,
    detached: bool = False,
):
    """Start a jupyter notebook on remote host."""

    print = console.log

    REMOTE_HOME = f"/home/{c.user}"
    if notebook_dir is None:
        notebook_dir = REMOTE_HOME
    output_folder = f"{REMOTE_HOME}/straxlab"

    local_port = get_open_port(start=local_port)
    env_vars = {}

    if local_cutax:
        env_vars["INSTALL_CUTAX"] = "0"

    with console.status("Creating straxlab folder..."):
        c.run("mkdir -p " + output_folder)

    log_fn = output_folder + "/jupyter.log"

    if env == "singularity":
        s_container = "xenonnt-%s.simg" % tag
        starter_path = f"{output_folder}/start_notebook.sh"
        starter_script = StringIO(START_NOTEBOOK_SH)
        with console.status(f"Copying starter script to {c.host}:{starter_path} ..."):
            c.put(starter_script, remote=starter_path)
        with console.status("Making starter script executable..."):
            c.run(f"chmod +x {starter_path}")

        batch_job = (
            JOB_HEADER + "{starter_path} "
            "{s_container} {jupyter} {nbook_dir}".format(
                starter_path=starter_path,
                s_container=s_container,
                jupyter=jupyter,
                nbook_dir=notebook_dir,
            )
        )
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

    url = None
    url_cache_fn = REMOTE_HOME + "/.last_jupyter_url"
    username = c.user

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
        with console.status(
            "Notebook reservation requested. Checking availability..."
        ):
            result = c.run("scontrol show reservations", hide=True, warn=True)
            if result.failed or "ReservationName=xenon_notebook" not in result.stdout:
                print("Notebook reservation does not exist, submitting a regular job.")
                use_reservation = False

    unique_id = "".join(choices(ascii_lowercase, k=6))
    with console.status("Checking for existing jobs..."):
        result = c.run(f"squeue -u {c.user} -n straxlab", hide=True, warn=True)
        df = parse_squeue_output(result.stdout)
        if len(df):
            job_fn = "/".join([output_folder, f"notebook_{unique_id}.sbatch"])
        else:
            job_fn = "/".join([output_folder, "notebook.sbatch"])
    if not force_new:
        log_fn = "/".join([output_folder, "notebook.log"])
    else:
        log_fn = "/".join([output_folder, f"notebook_forced_{unique_id}.log"])

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
            raise RuntimeError("Job did not start within %d seconds." % timeout)

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
                if "http://" in line and "?token=" in line:
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
                "Jupyter server did not start within %d seconds." % timeout
            )

        print("\nJupyter started succesfully.")
        print(f"\t Remote URL: {url}")
        remote_host, remote_port = url.split("/")[2].split(":")
        if "token" in url:
            token = url.split("?")[1].split("=")[1]
        else:
            token = ""

    local_url = f"http://localhost:{local_port}?token={token}"
    msg = f"Forwarding remote address {remote_host}:{remote_port} to local port {local_port}..."
    with console.status(msg) as status:
        print(f"You can access the notebook at {local_url}\n")

        if detached:
            c.local(
                f"ssh -fN -L {local_port}:{remote_host}:{remote_port} {c.user}@{c.host} &",
                disown=True,
                hide=False,
                warn=True,
            )
            time.sleep(3)
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
    print("Goodbye!")

import uuid
from io import BytesIO
from typing import List

from fabric.connection import Connection
from fabric.tasks import task

from xefab.utils import console

SBATCH_INSTRUCTIONS = {
    "partition": "partition to submit the job to.",
    "qos": "quality of service to submit the job to.",
    "time": "number of hours to run the job for, can be a `hrs:mins:secs` string or a number.",
    "mem_per_cpu": "memory per cpu.",
    "cpus_per_task": "number of cpus per task.",
    "jobname": "name of the job.",
    "job": "jobscript to run.",
    "output": "where to save the output of the job.",
    "error": "where to save the error of the job.",
    "account": "account to submit the job to.",
}

SINGULARITY_ARGUMENTS = {
    "bind": "binds a directory to the container.",
}

sbatch_template = """#!/bin/bash
#SBATCH --job-name={jobname}
#SBATCH --output={log}
#SBATCH --error={log}
#SBATCH --account=pi-lgrandi
#SBATCH --qos={qos}
#SBATCH --partition={partition}
#SBATCH --mem-per-cpu={mem_per_cpu}
#SBATCH --cpus-per-task={cpus_per_task}
{hours}
{job}
"""


def generate_slurm_instructions(**kwargs):
    """Generates the instructions for the sbatch script"""
    instructions = []
    for key, value in kwargs.items():
        if key in SBATCH_INSTRUCTIONS:
            key = key.replace("_", "-")
            if key == "time":
                if not ":" in value:
                    value = f"{value}:00:00"
                if isinstance(value, int):
                    value = f"{value:02d}:00:00"
                elif isinstance(value, float):
                    value = f"{int(value):02d}:{int(value * 60 % 60):02d}:{int(value * 60 % 60 * 60 % 60):02d}"
                instructions.append(f"#SBATCH --time={value}")
            else:
                instructions.append(f"#SBATCH --{key}={value}")

    return "\n".join(instructions) + "\n"


def generate_singularity_instructions(command, image_path, **kwargs):
    """Generates the instructions for the singularity exec"""
    instructions = ["singularity exec"]
    for key, value in kwargs.items():
        if key in SINGULARITY_ARGUMENTS:
            if key == "bind":
                if isinstance(value, str):
                    value = value.split(",")
                bind_str = " ".join([f"--bind {b}" for b in value])
                instructions.append(bind_str)
            else:
                instructions.append(f"--{key}={value}")

    instructions.append(image_path)
    instructions.append(command)

    return " ".join(instructions)


SINGULARITY_DIR = "/project2/lgrandi/xenonnt/singularity-images"


def singularity_wrap(
    c: Connection, jobstring: str, tmpdir: str, image: str, bind: List[str] = []
):
    """Wraps a jobscript into another executable
    file that can be passed to singularity exec"""

    if isinstance(bind, str):
        bind = [bind]

    bind = list(bind) + [tmpdir]

    filename = "xefabtmp_" + f"{uuid.uuid4()}.sh".replace("-", "")[-10:]

    filepath = "/".join([tmpdir, filename])

    console.print(f"Using {filepath} on {c.host} for inner jobscript.")

    with console.status(f"Uploading inner jobscript to {filepath} on {c.host}"):
        fd = BytesIO(f"#!/bin/bash\n{jobstring}".encode())
        c.put(fd, remote=filepath)
        del fd

    with console.status(f"Changing {filepath} on {c.host} to executable"):
        c.run(f"chmod +x {filepath}")

    bind_string = " ".join([f"--bind {b}" for b in bind])
    image = "/".join([SINGULARITY_DIR, image])

    new_job_string = f"""singularity exec {bind_string} {image} {filepath}
rm {filepath}
"""
    return new_job_string


@task(
    help={
        "command": "the command to execute within the job.",
        "partition": "partition to submit the job to.",
        "qos": "qos to submit the job to.",
        "account": "account to submit the job to.",
        "jobname": "how to name this job.",
        "dry_run": "Just print the job file.",
        "mem_per_cpu": "mb requested for job.",
        "container": "name of the container to activate",
        "bind": "which paths to add to the container",
        "cpus_per_task": "cpus requested for job",
        "hours": "max hours of a job",
    }
)
def submit_job(
    c: Connection,
    command: str,
    *,
    partition="xenon1t",
    qos="xenon1t",
    account="pi-lgrandi",
    jobname="xefab_job",
    dry_run=False,
    mem_per_cpu=1000,
    container="xenonnt-development.simg",
    bind=("/dali", "/project2"),
    cpus_per_task=1,
    hours=None,
):
    """
    Create and submit a job to SLURM job queue on the remote host.
    """
    console.print(f"Using {c.host} as host")
    console.print(f"job command: {command}")

    with console.status(f"Looking up SCRATCH directory on {c.host}"):
        result = c.run("echo $SCRATCH", hide=True, warn=True)
        if result.ok and result.stdout:
            TMPDIR = result.stdout.strip()
        else:
            TMPDIR = "."

    TMPDIR = "/".join([TMPDIR, "tmp"])

    console.print(f"Using {TMPDIR} as temporary directory")

    with console.status(f"Creating temporary directory {TMPDIR} on {c.host}"):
        c.run(f"mkdir -p {TMPDIR}", hide=True, warn=True)

    console.print(f"Created temporary directory {TMPDIR} on {c.host}")

    random_string = f"{uuid.uuid4()}".replace("-", "")[-8:]

    batchname = f"{jobname}_{random_string}"

    if container:
        # need to wrap job into another executable
        jobstr = singularity_wrap(c, command, TMPDIR, container, bind)
        jobstr = (
            "unset X509_CERT_DIR CUTAX_LOCATION\n"
            + "module load singularity\n"
            + jobstr
        )
    else:
        jobstr = command

    if hours is not None:
        hours = "#SBATCH --time={:02d}:{:02d}:{:02d}".format(
            int(hours), int(hours * 60 % 60), int(hours * 60 % 60 * 60 % 60)
        )
    else:
        hours = ""

    sbatch_file = f"{batchname}.sbatch"
    log = f"{batchname}.log"

    sbatch_script = sbatch_template.format(
        jobname=jobname,
        log=log,
        qos=qos,
        partition=partition,
        account=account,
        job=jobstr,
        mem_per_cpu=mem_per_cpu,
        cpus_per_task=cpus_per_task,
        hours=hours,
    )

    if dry_run:
        console.print("=== DRY RUN ===")
        console.print(sbatch_script)
        return

    console.print(f"Using {sbatch_file} as sbatch filename")

    with console.status(f"Uploading outer jobscript to {sbatch_file} on {c.host}"):
        fd = BytesIO(sbatch_script.encode())
        c.put(fd, remote=sbatch_file)

    command = "sbatch %s" % sbatch_file
    with console.status(f"Executing {command} on {c.host}"):
        result = c.run(command, hide=True, warn=True)
        if result.ok and result.stdout:
            job_id = result.stdout.strip()
            console.print(f"Job ID: {job_id}")

    with console.status(f"Removing {sbatch_file} on {c.host}"):
        c.run(f"rm {sbatch_file}", hide=True, warn=True)

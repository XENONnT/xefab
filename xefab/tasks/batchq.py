import json
import time
import uuid
from io import BytesIO, StringIO
from typing import List

from fabric.connection import Connection
from fabric.tasks import task
from rich.panel import Panel

from xefab.tasks.shell import exists, is_file
from xefab.tasks.squeue import parse_squeue_output
from xefab.utils import ProgressContext, console, tail

SLURM_INSTRUCTIONS = {
    "partition": "partition to submit the job to.",
    "qos": "quality of service to submit the job to.",
    "time": "number of hours to run the job for, can be a `hrs:mins:secs` string or a number.",
    "mem_per_cpu": "memory per cpu.",
    "cpus_per_task": "number of cpus per task.",
    "job_name": "name of the job.",
    "job": "jobscript to run.",
    "output": "where to save the output of the job.",
    "error": "where to save the error of the job.",
    "account": "account to submit the job to.",
    "chdir": "change directory to this path before running the job.",
    "mail_type": "when to send an email about the job.",
    "mail_user": "email address to send the email to.",
    "array": "array of jobs to run.",
    "dependency": "job dependency.",
    "exclude": "nodes to exclude.",
    "gres": "generic resources to use.",
    "hint": "hint to the scheduler.",
    "kill_on_invalid_dep": "kill the job if the dependency is invalid.",
    "nodelist": "nodes to use.",
    "ntasks": "number of tasks to run.",
    "ntasks_per_node": "number of tasks per node.",
    "ntasks_per_core": "number of tasks per core.",
    "nodes": "number of nodes to use.",
    "overcommit": "overcommit resources.",
    "requeue": "requeue the job if it fails.",
    "reservation": "reservation to use.",
    "threads_per_core": "threads per core.",
    "wait": "wait for the job to finish.",
    "comment": "comment to add to the job.",
    "constraint": "constraint to use.",
    "get_user_env": "get the user environment.",
}

SINGULARITY_ARGUMENTS = {
    "bind": "binds a directory to the container.",
}


SBATCH_TEMPLATE = """#!/bin/bash
{slurm_instructions}

{env_settings}

unset X509_CERT_DIR CUTAX_LOCATION

module load singularity

{command}

echo {done_message}
echo "Finished at $(date)"
"""


def generate_slurm_instructions(**kwargs):
    """Generates the singularity command for the sbatch script"""
    instructions = []
    for key, value in kwargs.items():
        if key in SLURM_INSTRUCTIONS:
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
        if key not in SINGULARITY_ARGUMENTS:
            continue
        if key == "bind":
            if isinstance(value, str):
                value = value.split(",")
            bind_str = " ".join([f"--bind {b}" for b in value])
            instructions.append(bind_str)
        elif isinstance(value, bool):
            instructions.append(f"--{key}")
        else:
            instructions.append(f"--{key}={value}")

    instructions.append(image_path)
    instructions.append(command)

    return " ".join(instructions)


def generate_env_instructions(**env):
    """Generates the environment variables export commands for the job"""
    if not env:
        return ""
    instructions = []
    for key, value in env.items():
        instructions.append(f"export {key}={value}")

    return "\n".join(instructions) + "\n\n"


SINGULARITY_DIR = "/project2/lgrandi/xenonnt/singularity-images"


@task(
    help={
        "script": "the command/script to execute within the job.",
        "partition": "partition to submit the job to.",
        "qos": "qos to submit the job to.",
        "account": "account to submit the job to.",
        "job_name": "how to name this job.",
        "dry_run": "Just print the job file.",
        "mem_per_cpu": "mb requested for job.",
        "container": "name of the container to activate",
        "bind": "which paths to add to the container",
        "cpus_per_task": "cpus requested for job",
        "hours": "max hours of a job",
        "container_dir": "where to find the container",
        "env_dict": "environment variables to set before running the job",
        "workdir": "working directory for the job",
        "output": "where to save the stdout stream of the job",
        "error": "where to save the stderr stream of the job",
        "timeout": "how long to wait for the job to start before exiting (seconds)",
        "extra_instructions": "extra slurm instructions to add to the batch file",
    }
)
def sbatch(
    c: Connection,
    script: str,
    *,
    partition: str = "xenon1t",
    qos: str = "xenon1t",
    account: str = "pi-lgrandi",
    job_name: str = None,
    dry_run: bool = False,
    mem_per_cpu: int = 1000,
    container="xenonnt-development.simg",
    bind: list = None,
    cpus_per_task: int = 1,
    hours: float = 12,
    container_dir: str = SINGULARITY_DIR,
    env_dict: str = None,
    workdir: str = None,
    output: str = None,
    error: str = None,
    extra_instructions: str = None,
    timeout: int = 120,
):
    """
    Create and submit a job to SLURM job queue on the remote host.
    """

    job_id = str(uuid.uuid4()).replace("-", "")[:8]

    if job_name is None:
        job_name = f"xefab_job_{job_id}"

    if partition == "kicp":
        qos = "xenon1t-kicp"
    else:
        qos = partition

    # parse and check arguments

    if bind is None:
        bind = ["/dali", "/project2", "/scratch", "/cvmfs"]
    if len(bind) == 1:
        bind = bind[0].split(",")
    bind = [b.strip() for b in bind]

    if env_dict is None:
        env_dict = {}
    else:
        env_dict = json.loads(env_dict)

    if extra_instructions is None:
        extra_instructions = {}
    else:
        extra_instructions = json.loads(extra_instructions)

    with ProgressContext() as progress:
        if workdir is None:
            with progress.enter_task("Checking for $SCRATCH folder") as task:
                result = c.run("echo $SCRATCH", hide=True, warn=True)
            if result.ok and result.stdout:
                SCRATCH = result.stdout.strip()
            else:
                SCRATCH = f"/scratch/midway2/{c.user}"

            workdir = f"{SCRATCH}/xefab_jobs/{job_name}"

        if output is None:
            output = f"{workdir}/{job_name}.out"
        if error is None:
            error = f"{workdir}/{job_name}.err"

        if script.endswith(".py"):
            remote_script_path = f"{workdir}/{job_name}.py"
            command = f"python {remote_script_path}"
        else:
            remote_script_path = f"{workdir}/{job_name}.sh"
            command = remote_script_path

        sbatch_path = f"{workdir}/{job_name}.sbatch"

        with progress.enter_task(
            "Testing remote connection and workdir existince"
        ) as task:
            if not exists(c, workdir, hide=True):
                progress.update(
                    task, description=f"Creating workdir {workdir} on {c.host}"
                )
                c.run(f"mkdir -p {workdir}", hide=True)

        if is_file(c, script, hide=True, local=True):
            with progress.enter_task(f"Copying script to {c.original_host}"):
                c.put(script, remote=remote_script_path)

        elif is_file(c, script, hide=True):
            with progress.enter_task(f"Copying script to working directory"):
                c.run(f"cp {script} {remote_script_path}", hide=True)
        else:
            script_fd = StringIO("#!/bin/bash\n" + script)
            with progress.enter_task(f"Creating script at on {c.original_host}"):
                c.put(script_fd, remote=remote_script_path)

        if remote_script_path.endswith("sh"):
            with progress.enter_task(f"Making script executable"):
                c.run(f"chmod +x {remote_script_path}", hide=True)

        with progress.enter_task(f"Creating sbatch file"):
            slurm_instructions = generate_slurm_instructions(
                job_name=job_name,
                partition=partition,
                qos=qos,
                account=account,
                mem_per_cpu=mem_per_cpu,
                cpus_per_task=cpus_per_task,
                hours=hours,
                output=output,
                error=error,
                chdir=workdir,
                **extra_instructions,
            )

            env_instructions = generate_env_instructions(**env_dict)

            if container:
                image_path = f"{container_dir.rstrip('/')}/{container}"
                command = generate_singularity_instructions(
                    command, image_path, bind=bind
                )

            done_message = f"Job {job_name} done."

            sbatch_content = SBATCH_TEMPLATE.format(
                slurm_instructions=slurm_instructions,
                env_settings=env_instructions,
                command=command,
                done_message=done_message,
            )

        if dry_run:
            progress.live_display(Panel.fit(sbatch_content, title="sbatch file"))
            exit(0)

        with progress.enter_task(f"Uploading sbatch file to {c.original_host}"):
            sbatch_fd = StringIO(sbatch_content)
            c.put(sbatch_fd, remote=sbatch_path)

        with progress.enter_task(f"Making sbatch file executable"):
            c.run(f"chmod +x {sbatch_path}", hide=True)

        with progress.enter_task(f"Submitting job to SLURM queue") as task:
            result = c.run(f"sbatch {sbatch_path}", hide=True, warn=True)
            if result.ok and result.stdout:
                job_id = int(result.stdout.split()[-1])
                progress.update(
                    task, description=f"Job submitted to batch queue. Job ID: {job_id}"
                )
            else:
                raise RuntimeError("Job submission failed.\n" + result.stdout)

        with progress.enter_task(f"Waiting for job to start") as task:
            for _ in range(timeout):
                result = c.run(f"squeue -j {job_id}", hide=True, warn=True)
                df = parse_squeue_output(result.stdout)
                if len(df) and df["ST"].iloc[0] == "R":
                    progress.update(task, description=f"Job started")
                    break
                elif len(df) and df["ST"].iloc[0] == "C":
                    raise RuntimeError("Job was cancelled.")
                time.sleep(0.5)
            else:
                raise RuntimeError("Timeout reached while waiting for job to start.")

        with progress.enter_task(f"Waiting for job to finish") as task:
            for _ in range(hours * 3600 // 2):
                time.sleep(2)
                if not is_file(c, output, hide=True):
                    continue
                result = c.run(f"tail -n 5 {output}", hide=True, warn=True)
                if result.ok and result.stdout:
                    progress.live_display(Panel.fit(result.stdout, title="Output file"))
                if done_message in result.stdout:
                    progress.update(task, description=f"Output file ready")
                    progress.live_display(None)
                    break

        with progress.enter_task(f"Getting output files") as task:
            result = c.run(f"cat {output}", hide=True, warn=True)
            if result.ok and result.stdout:
                out = tail(result.stdout, 50)
                progress.console.print(Panel(out, title="Output file"))
            result = c.run(f"cat {error}", hide=True, warn=True)
            if result.ok and result.stdout:
                err = tail(result.stdout, 50)
                progress.console.print(Panel(err, title="Error file"))

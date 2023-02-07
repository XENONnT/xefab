from io import BytesIO, StringIO
import os
import tempfile
from typing import List
import uuid
from xefab.utils import console
from fabric.tasks import task
from fabric.connection import Connection


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

SINGULARITY_DIR = '/project2/lgrandi/xenonnt/singularity-images'

def singularity_wrap(c: Connection, 
                    jobstring: str, tmpdir: str,
                    image: str, bind: List[str] = []):
    """Wraps a jobscript into another executable 
    file that can be passed to singularity exec"""

    if isinstance(bind, str):
        bind = [bind]

    bind = list(bind) + [tmpdir]

    filename = "xefabtmp_" + f"{uuid.uuid4()}.sh".replace('-', '')[-10:]
    
    filepath = '/'.join([tmpdir, filename])
    
    console.print(f'Using {filepath} on {c.host} for inner jobscript.')
    
    with console.status(f'Uploading inner jobscript to {filepath} on {c.host}'):
        fd = BytesIO(f'#!/bin/bash\n{jobstring}'.encode())  
        c.put(fd, remote=filepath)
        del fd
    
    with console.status(f'Changing {filepath} on {c.host} to executable'):
        c.run(f'chmod +x {filepath}')
    
    bind_string = " ".join([f"--bind {b}" for b in bind])
    image = '/'.join([SINGULARITY_DIR, image])

    new_job_string = f"""singularity exec {bind_string} {image} {filepath}
rm {filepath}
"""
    return new_job_string

@task
def submit_job(c: Connection,
               command: str,
               *,
               partition='xenon1t',
               qos='xenon1t',
               account='pi-lgrandi',
               jobname='xefab_job',
               dry_run=False,
               mem_per_cpu=1000,
               container='xenonnt-development.simg',
               bind=('/dali', '/project2'),
               cpus_per_task=1,
               hours=None,
               ):
    """
    Submit a job to the dali batch queue
    EXAMPLE
        from utilix import batchq
        import time
        job_log = 'job.log'
        batchq.submit_job('echo "say hi"', log=job_log)
        time.sleep(10) # Allow the job to run
        for line in open(job_log):
            print(line)
    :param jobstring: the command to execute
    :param partition: partition to submit the job to
    :param qos: qos to submit the job to
    :param account: account to submit the job to
    :param jobname: how to name this job
    :param dry_run: only print how the job looks like
    :param mem_per_cpu: mb requested for job
    :param container: name of the container to activate
    :param bind: which paths to add to the container
    :param cpus_per_task: cpus requested for job
    :param hours: max hours of a job
    :param kwargs: are ignored
    :return: None
    """
    console.print(f'Using {c.host} as host')
    console.print(f"job command: {command}")

    with console.status(f'Looking up SCRATCH directory on {c.host}'):
        result = c.run('echo $SCRATCH', hide=True, warn=True)
        if result.ok and result.stdout:
            TMPDIR = result.stdout.strip()
        else:
            TMPDIR = '.'

    TMPDIR = '/'.join([TMPDIR, 'tmp'])

    console.print(f'Using {TMPDIR} as temporary directory')

    with console.status(f'Creating temporary directory {TMPDIR} on {c.host}'):
        c.run(f'mkdir -p {TMPDIR}', hide=True, warn=True)
    
    console.print(f'Created temporary directory {TMPDIR} on {c.host}')

    random_string = f"{uuid.uuid4()}".replace('-', '')[-8:]

    batchname = f"{jobname}_{random_string}"

    if container:
        # need to wrap job into another executable
        jobstr = singularity_wrap(c, command, TMPDIR, container, bind)
        jobstr = 'unset X509_CERT_DIR CUTAX_LOCATION\n' + 'module load singularity\n' + jobstr
    else:
        jobstr = command

    if hours is not None:
        hours = '#SBATCH --time={:02d}:{:02d}:{:02d}'.format(int(hours), int(hours * 60 % 60), int(hours * 60 % 60 * 60 % 60))
    else:
        hours = ''

    sbatch_file = f"{batchname}.sbatch"
    log = f"{batchname}.log"

    sbatch_script = sbatch_template.format(jobname=jobname, log=log, qos=qos, partition=partition,
                                           account=account, job=jobstr, mem_per_cpu=mem_per_cpu,
                                           cpus_per_task=cpus_per_task, hours=hours)

    if dry_run:
        console.print("=== DRY RUN ===")
        console.print(sbatch_script)
        return        

    console.print(f'Using {sbatch_file} as sbatch filename')

    with console.status(f'Uploading outer jobscript to {sbatch_file} on {c.host}'):
        fd = BytesIO(sbatch_script.encode())
        c.put(fd, remote=sbatch_file)


    command = "sbatch %s" % sbatch_file
    with console.status(f'Executing {command} on {c.host}'):
        result = c.run(command, hide=True, warn=True)
        if result.ok and result.stdout:
            job_id = result.stdout.strip()
            console.print(f'Job ID: {job_id}')

    with console.status(f'Removing {sbatch_file} on {c.host}'):
        c.run(f'rm {sbatch_file}', hide=True, warn=True)

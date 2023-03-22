import json
import time
from io import StringIO

from fabric.tasks import task
from invoke.watchers import Responder
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Confirm

from xefab.utils import ProgressContext, console

from .github import clone
from .shell import exists
from .utils import print_splash


@task(pre=[print_splash])
def mc_chain(
    c,
    simulation_name: str = "Pmt_neutron",
    start_job: int = 0,
    num_events: int = 1000,
    jobs_per_batch: int = 5,
    events_per_job: int = 100,
    experiment: str = "XENONnT",
    mc_version: str = "head",
    mc_preinit_macro: str = "preinit_nVeto.mac",
    mc_preinit_belt: str = "preinit_B_none.mac",
    mc_optical_setup: str = "setup_optical.mac",
    mc_source_macro: str = "run_Cryostat_neutron.mac",
    run_wfsim: bool = False,
    epix_detectorconfig: str = "sr0_epix_detectorconfig.ini",
    epix_microseparation: float = 0.05,
    epix_tagclusterby: str = "energy",
    epix_nr_only: bool = False,
    event_rate: float = 1,
    chunk_size: int = 100,
    save_raw_records: bool = False,
    run_fast_sim: bool = False,
    sim_nv: bool = False,
    config_file: str = None,
):
    """Run a full chain MC simulation"""

    if config_file is None:
        config = {
            "simulation_name": simulation_name,
            "start_job": start_job,
            "num_events": num_events,
            "jobs_per_batch": jobs_per_batch,
            "events_per_job": events_per_job,
            "experiment": experiment,
            "mc_version": mc_version,
            "mc_preinit_macro": mc_preinit_macro,
            "mc_preinit_belt": mc_preinit_belt,
            "mc_optical_setup": mc_optical_setup,
            "mc_source_macro": mc_source_macro,
            "run_wfsim": run_wfsim,
            "epix_detectorconfig": epix_detectorconfig,
            "epix_microseparation": epix_microseparation,
            "epix_tagclusterby": epix_tagclusterby,
            "epix_nr_only": epix_nr_only,
            "event_rate": event_rate,
            "chunk_size": chunk_size,
            "save_raw_records": save_raw_records,
            "run_fast_sim": run_fast_sim,
            "sim_nv": sim_nv,
        }

        config_file = StringIO(json.dumps(config, indent=4))

    PRODUCTION_DIR = f"/scratch/{c.user}/simulations"
    repo_dir = f"{PRODUCTION_DIR}/mc_chain"
    config_file_remote_path = f"{repo_dir}/{simulation_name}_config.json"
    with ProgressContext() as progress:
        # Check if the production directory exists
        if not exists(c, repo_dir, hide=True):
            # Create the production directory
            with progress.enter_task("Creating production directory"):
                c.run(f"mkdir -p {PRODUCTION_DIR}", hide=True)

            # Clone the MC repo
            with progress.enter_task("Cloning MC repo"):
                clone(c, repo="mc_chain", dest=repo_dir, hide=True)

        # Copy the config file
        with progress.enter_task("Uploading config file"):
            r = c.put(config_file, remote=config_file_remote_path)

        # FIXME: Do we need to renew the user proxy? or just use the shared xenon one?
        # with progress.enter_task("Renewing user certificate proxy"):
        #     password = console.input("Enter GRID pass phrase for this identity:")
        #     responder = Responder(
        #             pattern=r"Enter GRID pass phrase for this identity:",
        #             response=password,
        #             )
        #     c.run("voms-proxy-init -voms xenon.biggrid.nl -bits 2048 -hours 168 --debug -out ~/user_cert",
        #             hide=True, watchers=[responder])

        # Switch to the repo directory
        with c.cd(repo_dir):
            # Setup the environment
            with c.prefix("source setup_env.sh"):
                # Run the chain
                with progress.enter_task("Bulding and submiting workflow"):
                    result = c.run(
                        f"python mc_chain.py --config {config_file_remote_path} --skip-rucio",
                        out_stream=progress.console.file,
                        hide=False,
                    )
                    if result.failed:
                        console.print("Error while building and submitting workflow")
                        console.print(result.stdout)
                        return
        status_command = None
        remove_command = None
        for line in result.stdout.splitlines():
            if "pegasus-status" in line:
                status_command = line.strip()
            if "pegasus-remove" in line:
                remove_command = line.strip()
        try:
            msg = Text("Press Ctrl+C to exit.", style="bold red")
            with progress.enter_task(
                "Monitoring status",
            ):
                while True:
                    result = c.run(status_command, hide=True)
                    status = Panel.fit(result.stdout, title="Workflow Status")
                    display = Group(status, msg)
                    progress.live_display(display)
                    for line in result.stdout.splitlines():
                        if "no matching jobs found in Condor Q" in line:
                            exit(0)
                    time.sleep(2)
        except KeyboardInterrupt:
            pass

        except Exception as e:
            console.print(e)
    if remove_command is not None:        
        cancel = Confirm.ask("Cancel workflow?")
        if cancel:
            with c.cd(repo_dir):
                with c.prefix("source setup_env.sh"):
                    c.run(f"{remove_command}")
    console.print("Goodbye!")

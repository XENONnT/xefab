from typing import List
from importlib_resources import files

from xefab.file_access import TemplateFile


class RunSim(TemplateFile):
    __TEMPLATE__ = files("data.mc_chain").joinpath("run_sim.sh").read_text()

    filename = "run_sim.sh"
    job_id: str
    starting_event: str
    events_to_simulate: str
    experiment: str
    mc_version: str
    mc_preinit_macro: str
    mc_preinit_belt: str
    mc_optical_setup: str
    mc_source_macro: str
    simulation_name: str

class Merge(TemplateFile):
    
    __TEMPLATE__ = files("data.mc_chain").joinpath("merge.sh").read_text()

    filename = "merge.sh"
    run_id: str
    inputs: List[str]


class RunWfSim(TemplateFile):
    __TEMPLATE__ = files("data.mc_chain").joinpath("run_wfsim-wrapper.sh").read_text()

    filename = "run_wfsim.sh"
    input_tarball: str
    experiment: str
    sim_nv: str
    entry_start: str
    entry_stop: str
    event_rate: str
    chunk_size: str
    epix_microseparation: str
    epix_tagclusterby: str
    epix_nronly: str
    save_raw_records: str
    mcversion: str
    local_test: str
    epix_detectorconfig: str


class MergeWfSim(TemplateFile):
    __TEMPLATE__ = files("data.mc_chain").joinpath("merge_wfsim-wrapper.sh").read_text()

    filename = "merge_wfsim.sh"
    batch_number: str
    output_tarball: str
    sim_nv: str
    epix_microseparation: str
    epix_tagclusterby: str
    epix_nronly: str
    epix_detectorconfig: str


class UploadWrapper(TemplateFile):
    __TEMPLATE__ = files("data.mc_chain").joinpath("upload_wrapper.sh").read_text()

    filename = "upload_wrapper.sh"
    config_file: str

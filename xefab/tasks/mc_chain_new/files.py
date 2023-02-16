from typing import List
from importlib_resources import files

from xefab.file_access import TemplateFile


class RunSim(TemplateFile):
    __NAME__ = "run_sim.sh"
    __TEMPLATE__ = files("data.mc_chain").joinpath("run_sim.sh").read_text()

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
    __NAME__ = "merge.sh"
    __TEMPLATE__ = files("data.mc_chain").joinpath("merge.sh").read_text()

    run_id: str
    inputs: List[str]


class RunWfSim(TemplateFile):
    __NAME__ = "run_wfsim.sh"
    __TEMPLATE__ = files("data.mc_chain").joinpath("run_wfsim-wrapper.sh").read_text()

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
    __NAME__ = "merge_wfsim.sh"
    __TEMPLATE__ = files("data.mc_chain").joinpath("merge_wfsim-wrapper.sh").read_text()

    batch_number: str
    output_tarball: str
    sim_nv: str
    epix_microseparation: str
    epix_tagclusterby: str
    epix_nronly: str
    epix_detectorconfig: str


class UploadWrapper(TemplateFile):
    __NAME__ = "upload_wrapper.sh"
    __TEMPLATE__ = files("data.mc_chain").joinpath("upload_wrapper.sh").read_text()

    config_file: str

from typing import List, Literal
from importlib_resources import files

from xefab.file_access import TemplateFile


class RunSim(TemplateFile):
    __TEMPLATE__ = files("xefab.data.mc_chain").joinpath("run_sim.sh").read_text()

    filename: str = "run_sim.sh"
    simulation_name: str
    job_id: str
    starting_event: str
    events_to_simulate: str
    experiment: str
    mc_version: str
    mc_preinit_macro: str = "preinit_nVeto.mac"
    mc_preinit_belt: str = "preinit_B_none.mac"
    mc_optical_setup: str = "setup_optical.mac"
    mc_source_macro: str = "run_Cryostat_neutron.mac"
    

class Merge(TemplateFile):
    
    __TEMPLATE__ = files("xefab.data.mc_chain").joinpath("merge.sh")

    filename: str = "merge.sh"
    run_id: str
    inputs: List[str]

class RunWfSim(TemplateFile):
    __TEMPLATE__ = files("xefab.data.mc_chain").joinpath("run_wfsim-wrapper.sh")

    filename = "run_wfsim.sh"
    input_tarball: str
    experiment: Literal["XENONnT","XENON1T"] = "XENONnT"
    sim_nv: bool = True
    entry_start: str
    entry_stop: str
    event_rate: int = 1
    chunk_size: int = 100
    epix_microseparation: float = 0.05
    epix_tagclusterby: str = "energy"
    epix_nronly: bool = False
    save_raw_records: str
    mcversion: str = "head"
    local_test: bool = False
    epix_detectorconfig: str = "sr0_epix_detectorconfig.ini"


class MergeWfSim(TemplateFile):
    __TEMPLATE__ = files("xefab.data.mc_chain").joinpath("merge_wfsim-wrapper.sh")

    filename: str = "merge_wfsim.sh"
    batch_number: int = 0
    output_tarball: str
    sim_nv: bool = True
    epix_microseparation: float = 0.05
    epix_tagclusterby: str = "energy"
    epix_nronly: bool = False
    epix_detectorconfig: str = "sr0_epix_detectorconfig.ini"


class UploadWrapper(TemplateFile):
    __TEMPLATE__ = files("xefab.data.mc_chain").joinpath("upload-wrapper.sh")

    filename = "upload_wrapper.sh"
    config_file: str

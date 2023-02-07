import os

import appdirs
from fabric.config import Config as FabricConfig
from fabric.config import merge_dicts
from invoke.util import debug
from rich.console import Console

from xefab.entrypoints import get_entry_points
from xefab.utils import console


dirs = appdirs.AppDirs("xefab")

XEFAB_CONFIG = os.getenv(
    "XEFAB_CONFIG", os.path.join(dirs.user_config_dir, "config.env")
)


class Config(FabricConfig):
    """Settings for xefab."""

    prefix = "xefab"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("system_prefix", dirs.site_config_dir + '/')
        kwargs.setdefault("user_prefix", dirs.user_config_dir + '/')
        super().__init__(*args, **kwargs)

    def _get_ssh_config(self, hostname):
        """Look up the host in the SSH config, if it exists."""
        config = {"hostname": hostname}

        for host in self.base_ssh_config.get_hostnames():
            data = self.base_ssh_config.lookup(host)
            host_hostname = data.get("hostname", "")
            if hostname in [host, host_hostname]:
                config.update(data)
                return config

    def configure_ssh_for_host(self, host, hostnames=None):
        """Find the SSH config for a host."""
        if isinstance(hostnames, str):
            hostnames = hostnames.split(",")

        config = None
        if hostnames is None:
            config = self.base_ssh_config.lookup(host)

        elif not isinstance(hostnames, list):
            debug(
                "xefab: hostnames must be a list or a string,"
                f" got {type(hostnames)} for host {host}. Ignoring"
            )
            return

        self.load_ssh_config()

        for hostname in hostnames:
            config = self._get_ssh_config(hostname)
            if config is not None:
                debug(f"xefab: found ssh config for {hostname}")
                break
        else:
            config = {"hostname": hostname}

        ssh_config = {"host": host, "config": config}

        self.base_ssh_config._config.insert(0, ssh_config)

    @staticmethod
    def global_defaults():
        """Add extra parameters to the default dict."""

        defaults = FabricConfig.global_defaults()

        for ep in get_entry_points("xefab.config"):
            try:
                cfg = ep.load()
                if isinstance(cfg, dict):
                    merge_dicts(defaults, cfg)
            except Exception as e:
                debug(f"xefab: Error loading config from {ep.name}: {e}")
                continue

        ours = {
            "tasks": {
                "collection_name": "xefab",
            },
        }

        merge_dicts(defaults, ours)

        return defaults

import os

import appdirs
from invoke.util import debug
from rich.console import Console
from fabric.config import Config as FabricConfig, merge_dicts
from xefab.entrypoints import get_entry_points


dirs = appdirs.AppDirs("XEFAB")

XEFAB_CONFIG = os.getenv(
    "XEFAB_CONFIG", os.path.join(dirs.user_config_dir, "config.env")
)


class Config(FabricConfig):
    """Settings for xefab."""
    console: Console = Console()
    prefix = "xefab"
    
    def __init__(self, *args, **kwargs):
        console = kwargs.pop("console", None)
        if console is not None:
            self._set("console", console)
        kwargs.setdefault("system_prefix", dirs.site_config_dir)
        kwargs.setdefault("user_prefix", dirs.user_config_dir)
        super().__init__(*args, **kwargs)

    def _get_ssh_config(self, name, hostname):
        """Look up the host in the SSH config, if it exists."""
        config = {'hostname': hostname}
        for host in self.base_ssh_config.get_hostnames():
            data = self.base_ssh_config.lookup(host)
            if (host in [name, hostname]
                or hostname == data.get('hostname', None)):
                config.update(data)
                break
        return {'host': name, 'config': config}

    def configure_ssh_for_host(self, host, hostname=None):
        """Find the SSH config for a host."""
        if hostname is None:
            config = self.base_ssh_config.lookup(host)
        else:
            config = self._get_ssh_config(host, hostname)
        if config:
            self.base_ssh_config._config.insert(0, config)

    @staticmethod
    def global_defaults():
        """Add extra parameters to the default dict."""

        defaults = FabricConfig.global_defaults()

        for ep in get_entry_points('xefab.config'):
            try:
                cfg = ep.load()
                if isinstance(cfg, dict):
                    merge_dicts(defaults, cfg)
            except Exception as e:
                debug(f"xefab: Error loading config from {ep.name}: {e}")
                continue
        
        ours = {
            'console': Console(),
            'tasks': {
                'collection_name': 'xefab',
            }
        }

        merge_dicts(defaults, ours)

        return defaults

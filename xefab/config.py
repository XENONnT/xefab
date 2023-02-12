import configparser
import os
from pathlib import Path

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

    MONGO_CLIENTS = {}

    prefix = "xefab"
    xenon_config = None

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("system_prefix", dirs.site_config_dir + "/")
        kwargs.setdefault("user_prefix", dirs.user_config_dir + "/")
        super().__init__(*args, **kwargs)
        self.load_xenon_config()

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
            return

        if not isinstance(hostnames, list):
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

        if "user" not in config:
            config["user"] = console.input(f"Enter username for {hostname}: ")

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
                "collection_name": "xetasks",
            },
            "xenon_config_paths": Config.get_xenon_config_paths(),
            "list-depth": 3,
        }

        merge_dicts(defaults, ours)

        return defaults

    @staticmethod
    def get_xenon_config_paths():
        """Get the paths to the xenon config files.
        Files are read in order, so the last one takes precedence.
        """

        paths = [
            os.path.join(dirs.site_config_dir, ".xenon_config"),
            os.path.join(dirs.user_config_dir, ".xenon_config"),
            os.path.join(os.getcwd(), ".xenon_config"),
            os.getenv("XENON_CONFIG", "~/.xenon_config"),
        ]

        return paths

    def load_xenon_config(self):
        """Load the xenon config file."""
        self.xenon_config = configparser.ConfigParser()
        self.merge()  # Make sure we have the latest config
        paths = getattr(self, "xenon_config_paths", [])
        if isinstance(paths, str):
            paths = paths.split(",")
        if not isinstance(paths, list):
            raise ValueError("xenon_config_paths must be a list or a string")
        paths = [os.path.expanduser(path) for path in paths]
        loaded = self.xenon_config.read(paths)
        debug(f"xefab: loaded xenon config from {loaded}")

    def _mongo_client(self, experiment, url=None, user=None, password=None):
        import pymongo

        if experiment not in ["xe1t", "xent"]:
            raise ValueError(
                f"experiment must be 'xe1t' or 'xent'. You passed f{experiment}"
            )

        if not url:
            url = self.xenon_config.get("RunDB", f"{experiment}_url")
        if not user:
            user = self.xenon_config.get("RunDB", f"{experiment}_user")
        if not password:
            password = self.xenon_config.get("RunDB", f"{experiment}_password")

        # build other client kwargs
        max_pool_size = self.xenon_config.get("RunDB", "max_pool_size", fallback=100)
        socket_timeout = self.xenon_config.get(
            "RunDB", "socket_timeout", fallback=60000
        )
        connect_timeout = self.xenon_config.get(
            "RunDB", "connect_timeout", fallback=60000
        )

        uri = f"mongodb://{user}:{password}@{url}"
        if uri not in self.MONGO_CLIENTS:
            self.MONGO_CLIENTS[uri] = pymongo.MongoClient(
                uri,
                readPreference="secondaryPreferred",
                maxPoolSize=max_pool_size,
                socketTimeoutMS=socket_timeout,
                connectTimeoutMS=connect_timeout,
            )
        return self.MONGO_CLIENTS[uri]

    def _mongo_database(self, experiment, database=None, **kwargs):
        if not database:
            database = self.xenon_config.get("RunDB", f"{experiment}_database")
        client = self._mongo_client(experiment, **kwargs)
        return client[database]

    def _mongo_collection(self, experiment, collection, **kwargs):
        client = self._mongo_database(experiment, **kwargs)
        return client[collection]

    def xent_collection(self, collection="runs", **kwargs):
        return self._mongo_collection("xent", collection, **kwargs)

    def xe1t_collection(self, collection="runs_new", **kwargs):
        return self._mongo_collection("xe1t", collection, **kwargs)

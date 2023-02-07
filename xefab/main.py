"""Console script for xesites."""
import sys

from fabric.executor import Executor
from fabric.main import Fab
from invoke.collection import Collection
from invoke.util import debug

from xefab import __version__, tasks
from xefab.collection import XefabCollection
from xefab.config import Config


class XeFab(Fab):
    """XeSites CLI"""

    def parse_collection(self):
        if self.namespace is None:
            self.namespace = XefabCollection.from_module(tasks, name="root")
            self.namespace.load_objects_from_entry_points()

        if self.core.unparsed and self.core.unparsed[0] in self.namespace.collections:
            sitename = self.core.unparsed.pop(0)
            self.namespace = self.namespace.collections[sitename]
            hostnames = self.namespace._configuration.get("hostnames", None)
            debug(f"xefab: {sitename} hostnames: {hostnames}")
            self.config.configure_ssh_for_host(sitename, hostnames)
            if not self.args.hosts.value and hostnames is not None:
                self.args.hosts.value = sitename
        super().parse_collection()

    def list_tasks(self):
        super().list_tasks()

        if self.collection.name != "root":
            # We are not in the root collection.
            return

        tuples = []
        for name, collection in self.collection.collections.items():
            hostnames = collection.configuration().get("hostnames", [])
            if isinstance(hostnames, str):
                hostnames = hostnames.split(",")
            if hostnames:
                hostnames = ",".join(hostnames)
                tuples.append((name, hostnames))

        if tuples:
            print("\n Remote Hosts:\n")
            self.print_columns(tuples)


def make_program():
    return XeFab(
        name="xefab",
        version=__version__,
        executor_class=Executor,
        config_class=Config,
    )


program = make_program()


if __name__ == "__main__":
    sys.exit(program.run())  # pragma: no cover

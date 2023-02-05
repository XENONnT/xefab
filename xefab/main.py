"""Console script for xesites."""
import sys

from fabric.main import Fab
from fabric.executor import Executor
from invoke.collection import Collection
from invoke.util import debug
from xefab.config import Config
from xefab.collection import XefabCollection
from xefab import tasks, __version__


class XeFab(Fab):
    """XeSites CLI"""
    def parse_collection(self):
        if self.namespace is None:
            self.namespace = XefabCollection.from_module(tasks, name='root')
            self.namespace.load_objects_from_entry_points('xefab.tasks')

        if self.core.unparsed and self.core.unparsed[0] in self.namespace.collections:
            sitename = self.core.unparsed.pop(0)
            self.namespace = self.namespace.collections[sitename]
            hostname = self.namespace.configuration().get('hostname', None)
            debug(f"xefab: {sitename} hostname: {hostname}")
            self.config.configure_ssh_for_host(sitename, hostname)
            self.args.hosts.value = sitename
        super().parse_collection()

    def list_tasks(self):
        super().list_tasks()
        
        if getattr(self.collection, 'host', None):
            # We are not in local collection.
            return

        tuples = []
        for name, collection in self.collection.collections.items():
            hostname = collection.configuration().get('hostname', None)
            if hostname:
                tuples.append((name, hostname))

        if tuples:
            print('\n Remote Hosts:\n')
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

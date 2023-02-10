"""Console script for xesites."""
import inspect
import sys

from rich.tree import Tree
from rich.console import Group
from rich.text import Text
from rich.panel import Panel
from rich.console import group, NewLine
from rich.padding import Padding
from rich.table import Table

from fabric.executor import Executor
from fabric.main import Fab
from invoke.util import debug
from invoke.exceptions import Exit

from xefab import __version__, tasks
from xefab.collection import XefabCollection
from xefab.config import Config
from xefab.utils import console


@group()
def get_tuples_group(header, docstring, tuples = None):
    """Create a group of tuples."""
    yield Text(header, style="bold")
    yield NewLine()
    if docstring:
        yield Text(docstring, style="italic")
    yield NewLine()
    yield Text("Options: ", style="bold")
    grid = Table.grid(expand=True)
    grid.add_column()
    grid.add_column(justify='left')
    for line in tuples:
        grid.add_row(*line)
    yield grid


class XeFab(Fab):
    """XeFab CLI"""
    ROOT_COLLECTION_NAME = "root"
    USER_COLLECTION_NAME = "my-tasks"

    def parse_collection(self):

        user_namespace = None
        # Load any locally defined tasks
        if self.namespace is not None:
            user_namespace = self.namespace
        else:
            try:
                self.load_collection()
                user_namespace = self.collection
            except Exit:
                pass

        # Load the default tasks
        self.namespace = XefabCollection.from_module(tasks, name=self.ROOT_COLLECTION_NAME)
        self.namespace.load_objects_from_entry_points()
        if user_namespace is not None:
            for name, task in user_namespace.tasks.items():
                self.namespace.add_task(task, name=name)
            for name, collection in user_namespace.collections.items():
                self.namespace.add_collection(collection, name=name)

        if len(self.argv)>1:
            argv = [self.argv.pop(0)]
            original_argv = list(self.argv)
            while self.argv:
                arg = self.argv.pop(0)
                if arg in ['-h', '--help', '--list']:
                    argv.append(arg)
                    continue
                if "." in arg:
                    arg, _, rest = arg.partition(".")
                    self.argv.insert(0, rest)
                
                if arg in self.namespace.collections:
                    self.namespace = self.namespace.collections[arg]
                    hostnames = self.namespace._configuration.get("hostnames", None)
                    debug(f"xefab: {arg} hostnames: {hostnames}")
                    self.config.configure_ssh_for_host(arg, hostnames)
                    if not self.args.hosts.value and hostnames is not None:
                        self.args.hosts.value = arg
                else:
                    argv.append(arg)
                    argv.extend(self.argv)
                    break
            if argv != original_argv:
                self.argv = argv
                self.parse_core(argv)
                
        super().parse_collection()

    def task_panel(self, task, name, parents = ()):
        """Create a help panel for a specific task."""
        docstring = inspect.getdoc(task)
        if docstring is None:
            docstring = ""
        if name in self.parser.contexts:
            ctx = self.parser.contexts[name]
            tuples = ctx.help_tuples()
        elif parents and f"{'.'.join(parents)}.{name}" in self.parser.contexts:
            ctx = self.parser.contexts[f"{'.'.join(parents)}.{name}"]
            tuples = ctx.help_tuples()
        else:
            tuples = []
        header = "Usage: {} [--core-opts] {} {}[other tasks here ...]"
        options_str = "[--options]" if tuples else ""
        task_path = " ".join(parents+(name,))
        header = header.format(self.binary, task_path, options_str)
        content = get_tuples_group(header, docstring, tuples=tuples)
        
        return Panel(content, title=Text(name, style='bold', ), title_align='left')

    def task_tree(self, collection, tree = None, parents = ()):
        """Create a tree of tasks."""
        if tree is None:
            tree = Tree("Tasks")
        
        for name, task in collection.tasks.items():
            panel = self.task_panel(task, name, parents=parents+(collection.name,) )
            tree.add(panel)
        for name, subcollection in collection.collections.items():
            subtree = tree.add(name)
            self.task_tree(subcollection, tree=subtree, parents=parents+(name,) )
        return tree

    def collection_panel(self, collection, parents = ()):
        """Create a help panel for a specific collection."""
        panels = []
        for name, task in collection.tasks.items():
            panel = self.task_panel(task, name, parents=parents+(collection.name,) )
            panels.append(panel)
        return Group(*panels)

    def list_tasks(self):
        """List all tasks in the current namespace."""
        if self.collection.collections:
            console.print(Text(f"\n\nTask tree:\n", style="bold") )
            console.print(self.task_tree(self.collection))
        else:
            console.print(Text(f"\n\nAvailable tasks:\n", style="bold"))
            console.print(self.collection_panel(self.collection,))
        return 
    
    def print_columns(self, tuples, indent=0):
        """Print a list of tuples in columns."""
        grid = Table.grid(expand=True)
        grid.add_column()
        grid.add_column()
        for line in tuples:
            grid.add_row(*line)
        console.print(grid)

    def print_help(self):
        usage_suffix = "[<host>] <collection> task1 [--task1-opts] ... taskN [--taskN-opts]"
        if self.namespace is not None and self.namespace.name != self.ROOT_COLLECTION_NAME:
            usage_suffix = f"{self.namespace.name} <subcommand> [--subcommand-opts] ..."
        console.print("Usage: {} [--core-opts] {}".format(self.binary, usage_suffix))
        console.print("")
        console.print("Core options:")
        console.print("")
        self.print_columns(self.initial_context.help_tuples())
        if self.namespace is not None:
            self.list_tasks()


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

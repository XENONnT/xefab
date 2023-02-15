"""Console script for xesites."""
import inspect
import sys
from collections import defaultdict

# IMPORTANT: Must be imported before fabric for monkey patching to work
# isort: off
from xefab.ssh_client import SSHClient  # isort: skip

# isort: on

from fabric.executor import Executor
from fabric.main import Fab
from invoke.exceptions import Exit
from invoke.parser import Argument
from invoke.util import debug, helpline
from rich.console import Group, NewLine, group
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from xefab import __version__, tasks
from xefab.collection import XefabCollection
from xefab.config import Config
from xefab.utils import ProgressContext, console, nested_dict


@group()
def get_tuples_group(header, docstring, tuples=None):
    """Create a group of tuples."""
    yield Text(header, style="bold")
    yield NewLine()
    if docstring:
        yield Text(docstring, style="italic")
    yield NewLine()
    yield Text("Options: ", style="bold")
    grid = Table.grid(expand=True)
    grid.add_column()
    grid.add_column(justify="left")
    for line in tuples:
        grid.add_row(*line)
    yield grid


def help_tuples_to_grid(tuples):
    """Convert a list of tuples to a rich table."""
    grid = Table.grid(expand=True)
    grid.add_column(justify="left", style="bold")
    grid.add_column(
        justify="left",
        style="dim",
    )
    for line in tuples:
        grid.add_row(*line)
    return grid


class XeFab(Fab):
    """XeFab CLI"""

    ROOT_COLLECTION_NAME = "main"
    USER_COLLECTION_NAME = "my-tasks"

    def core_args(self):
        """Add xefab config to core args."""
        DEFAULTS = {
            "list-depth": 2,
            "list-format": "flat",
        }
        args = super().core_args()

        for arg in args:
            for name in arg.names:
                if name in DEFAULTS:
                    arg.default = DEFAULTS[name]

        my_args = [
            # Argument(
            #     names=("verbose", "v"),
            #     kind=int,
            #     incrementable=True,
            #     default=0,
            #     help="Increase verbosity of outputs.",
            # ),
        ]

        return args + my_args

    def task_args(self):
        return super().task_args()

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
        self.namespace = XefabCollection.from_module(
            tasks, name=self.ROOT_COLLECTION_NAME
        )
        self.namespace.load_objects_from_entry_points()
        if user_namespace is not None:
            for name, task in user_namespace.tasks.items():
                self.namespace.add_task(task, name=name)
            for name, collection in user_namespace.collections.items():
                self.namespace.add_collection(collection, name=name)

        hostname = None
        if len(self.argv) > 1:
            argv = [self.argv.pop(0)]
            original_argv = list(self.argv)
            while self.argv:
                arg = self.argv.pop(0)
                if arg in ["-h", "--help", "--list", "-v", "--verbose"]:
                    argv.insert(0, arg)
                    continue

                if "." in arg:
                    arg, _, rest = arg.partition(".")
                    self.argv.insert(0, rest)

                if arg in self.namespace.collections:
                    self.namespace = self.namespace.collections[arg]
                    hostnames = self.namespace._configuration.get("hostnames", None)
                    debug(f"xefab: {arg} hostnames: {hostnames}")
                    self.config.configure_ssh_for_host(arg, hostnames)
                    if hostnames is not None and hostname is None:
                        hostname = arg
                else:
                    argv.append(arg)
                    argv.extend(self.argv)
                    break

            if argv != original_argv:
                self.argv = argv
                self.parse_core(argv)

            # if we loaded a host collection, it sets the default host argument
            if not self.args.hosts.value and hostname is not None:
                self.args.hosts.value = hostname
        super().parse_collection()

    def task_panel(self, task, name, parents=None):
        """Create a help panel for a specific task."""
        if parents is None:
            parents = ()
        if isinstance(parents, str):
            parents = (parents,)
        if isinstance(parents, tuple):
            parents = [parents]
        docstring = inspect.getdoc(task)
        if docstring is None:
            docstring = ""
        tuples = []
        if name in self.parser.contexts:
            ctx = self.parser.contexts[name]
            tuples = ctx.help_tuples()
        elif parents:
            for parent in parents:
                if f"{'.'.join(parent)}.{name}" in self.parser.contexts:
                    ctx = self.parser.contexts[f"{'.'.join(parent)}.{name}"]
                    tuples = ctx.help_tuples()
                    break

        if len(parents) > 1:
            header = "{} [--core-opts] <Collection> {} {}[other tasks here ...]"
            host_str = ",".join([" ".join(parent) for parent in parents])
        else:
            header = "{} [--core-opts] {} {}[other tasks here ...]"
            host_str = ""
        options_str = "[--options]" if tuples else ""

        if len(parents) == 1:
            name = " ".join(parents[0] + (name,))
        header = header.format(self.binary, name, options_str)
        if host_str:
            header += f"\nCollection options: {host_str}"
        content = get_tuples_group(header, docstring, tuples=tuples)

        return Panel(
            content,
            title=Text(
                name,
                style="bold",
            ),
            title_align="left",
        )

    def task_tree(self, collection, tree=None, parents=()):
        """Create a tree of tasks."""
        if tree is None:
            tree = Tree("")

        if self.list_depth <= len(parents):
            return tree

        for name, task in collection.tasks.items():
            if self.list_format == "tree":
                panel = self.task_panel(
                    task, name, parents=parents + (collection.name,)
                )
                tree.add(panel)
            else:
                tree.add(name)
        for name, subcollection in collection.collections.items():
            subtree = tree.add(name)
            self.task_tree(subcollection, tree=subtree, parents=parents + (name,))
        return tree

    def unique_tasks(self, collection, parents=()):
        """Create a set of unique tasks."""
        tasks = set()
        for name, task in collection.tasks.items():
            tasks.add(task)

        for name, subcollection in collection.collections.items():
            tasks.update(self.unique_tasks(subcollection, parents=parents + (name,)))
        return tasks

    def find_task_paths(self, task, collection, parents=()):
        """Find all paths to a task."""
        paths = []
        for name, subtask in collection.tasks.items():
            if subtask == task:
                paths.append(parents)

        for name, subcollection in collection.collections.items():
            paths.extend(
                self.find_task_paths(task, subcollection, parents=parents + (name,))
            )
        return paths

    def collection_panel(self, collection, parents=()):
        """Create a help panel for a specific collection."""
        panels = []
        for task in self.unique_tasks(collection):
            task_paths = self.find_task_paths(task, collection)
            panel = self.task_panel(task, task.name, parents=task_paths)
            panels.append(panel)
        return Group(*panels)

    def list_flat(self):
        pairs = self._make_pairs(self.scoped_collection)
        self.display_with_columns(pairs=pairs)

    def _make_help_pairs(self, coll, nested=False):
        pairs = []
        for name, task in sorted(coll.tasks.items()):
            is_default = name == coll.default
            # Start with just the name and just the aliases, no prefixes or
            # dots.
            displayname = name
            aliases = list(map(coll.transform, sorted(task.aliases)))

            # Nested? add asterisks to default-tasks.
            if nested and is_default:
                displayname += "*"

            # Generate full name and help columns and add to pairs.
            alias_str = " ({})".format(", ".join(aliases)) if aliases else ""
            full = (displayname + alias_str).strip()
            help_str = (helpline(task) or "").strip()
            pairs.append((full, help_str))

        return pairs

    def _make_help_tree(self, coll, ancestors=None, tree=None):
        if tree is None:
            tree = Tree("")

        if ancestors is None:
            ancestors = ()

        if not ancestors and not coll.collections:
            grid = help_tuples_to_grid(self._make_help_pairs(coll))
            return grid

        grid = help_tuples_to_grid(self._make_help_pairs(coll))
        tree.add(grid)

        for name, collection in sorted(coll.collections.items()):
            subtree = tree.add(name)
            self._make_help_tree(
                collection, ancestors=ancestors + (coll.name,), tree=subtree
            )

        return tree

    def list_usage(self):
        """List all tasks in the current namespace and their details."""
        console.print(Text(f"\n\nAvailable Tasks:\n", style="bold"))
        console.print(self._make_help_tree(self.scoped_collection))
        console.print(Text(f"\n\nTask Usage:\n", style="bold"))
        console.print(
            self.collection_panel(
                self.scoped_collection,
            )
        )

    def list_nested(self):
        """List all tasks in the current namespace."""
        console.print(Text(f"\n\nAvailable Tasks:\n", style="bold"))
        console.print(self._make_help_tree(self.scoped_collection))

    def print_task_help(self, name):
        """Print help for a specific task."""
        if name in self.collection.tasks:
            task = self.collection.tasks[name]
        console.print(self.task_panel(task, name))

    def print_columns(self, tuples, indent=0):
        """Print a list of tuples in columns."""
        grid = Table.grid(expand=True)
        grid.add_column()
        grid.add_column()
        for line in tuples:
            grid.add_row(*line)
        console.print(grid)

    def print_help(self):
        usage_suffix = (
            "[<host>] [<subcommand>] task1 [--task1-opts] ... taskN [--taskN-opts]"
        )
        if (
            self.namespace is not None
            and self.namespace.name != self.ROOT_COLLECTION_NAME
        ):
            usage_suffix = f"{self.namespace.name} <subcommand> [--subcommand-opts] ..."
        console.print("Usage: {} [--core-opts] {}".format(self.binary, usage_suffix))
        console.print("")
        console.print("Core options:")
        console.print("")
        self.print_columns(self.initial_context.help_tuples())
        console.print("\n")
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

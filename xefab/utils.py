import contextlib
import errno
import os
import re
import socket
from collections import defaultdict
from inspect import Parameter
from typing import Iterable, Optional, Tuple, Union

import fsspec
import pandas as pd
from decopatch import DECORATED, function_decorator
from fabric.connection import Connection
from invoke.context import Context
from invoke.util import enable_logging
from makefun import wraps
from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.progress import (Progress, ProgressColumn, SpinnerColumn, Task,
                           TextColumn)
from rich.table import Table
from rich.theme import Theme

custom_theme = Theme({"info": "dim cyan", "warning": "magenta", "danger": "bold red"})

console = Console(theme=custom_theme)


SHELL_PROFILE_FILES = {
    "sh": ["~/.profile"],
    "bash": ["~/.profile", "~/.bash_profile"],
    "zsh": ["~/.profile", "~/.zprofile"],
}


if os.environ.get("XEFAB_DEBUG") in ("1", "true", "True"):
    enable_logging()


def nested_dict():
    """Create a nested defaultdict."""
    return defaultdict(nested_dict)


def camel_to_snake(name):
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


@function_decorator
def try_local(exception=Exception, f=DECORATED):
    """Try to run a task locally, if it fails, run it remotely.
    Can be used as a decorator or as a function.
    if the first argument after the function is a Connection
    the function is called immediately, otherwise a wrapper is returned.
    """
    extra = Parameter(
        "force_remote",
        kind=Parameter.POSITIONAL_OR_KEYWORD,
        annotation=bool,
        default=False,
    )

    @wraps(f, append_args=extra)
    def wrapper(c, *args, force_remote=False, **kwargs):
        if isinstance(c, Connection) and not force_remote:
            try:
                inv_ctx = Context(config=c.config)
                return f(inv_ctx, *args, **kwargs)
            except exception as e:
                console.print(f"Failed to run locally: {e}")
                console.print("Running remotely instead.")
        return f(c, *args, **kwargs)

    return wrapper


def filesystem(c: Union[Connection, Context], local: bool = False) -> fsspec.AbstractFileSystem:
    """Get a fsspec filesystem object from a fabric Connection/Invoke Context object."""
    if c is not None:
        root = c.cwd
    else:
        root = os.getcwd()
    if isinstance(c, Connection) and not local:
        return fsspec.filesystem(
            "sftp", host=c.host, username=c.user, port=c.port, **c.connect_kwargs
        )

    return fsspec.filesystem("file", root=root)


def get_open_port(start=5000, end=None, bind_address="", *socket_args, **socket_kwargs):
    if start < 1024:
        start = 1024

    if end is None:
        end = start + 10000
    port = start
    while port < end:
        try:
            with contextlib.closing(
                socket.socket(*socket_args, **socket_kwargs)
            ) as my_socket:
                my_socket.bind((bind_address, port))
                my_socket.listen(1)
                this_port = my_socket.getsockname()[1]
                return this_port
        except socket.error as error:
            if not error.errno == errno.EADDRINUSE:
                raise
        port += 1
    raise Exception("Could not find open port")


def df_to_table(
    pandas_dataframe: pd.DataFrame,
    rich_table: Table = None,
    show_index: bool = True,
    index_name: Optional[str] = None,
) -> Table:
    """Convert a pandas.DataFrame obj into a rich.Table obj.
    Args:
        pandas_dataframe (DataFrame): A Pandas DataFrame to be converted to a rich Table.
        rich_table (Table): A rich Table that should be populated by the DataFrame values.
        show_index (bool): Add a column with a row count to the table. Defaults to True.
        index_name (str, optional): The column name to give to the index column. Defaults to None, showing no value.
    Returns:
        Table: The rich Table instance passed, populated with the DataFrame values."""
    if rich_table is None:
        rich_table = Table(show_header=True, header_style="bold magenta")
    if show_index:
        index_name = str(index_name) if index_name else ""
        rich_table.add_column(index_name)

    for column in pandas_dataframe.columns:
        rich_table.add_column(str(column))

    for index, value_list in enumerate(pandas_dataframe.values.tolist()):
        row = [str(index)] if show_index else []
        row += [str(x) for x in value_list]
        rich_table.add_row(*row)

    return rich_table


class SuccessSpinnerColumn(SpinnerColumn):
    """A spinner column that shows a checkmark when the task
    is completed successfully or a x if not.
    """

    def render(self, task: Task) -> RenderableType:
        if task.finished:
            if task.fields.get("exception", None) is None:
                return "[bold green]✓[/bold green]"
            else:
                return "[bold red]✗[/bold red]"
        else:
            return super().render(task)


class ProgressContext(Progress):
    """A context manager for rich.progress.Progress.
    Allows entering a task context and task will be completed when exiting
    """

    def __init__(self, *args, **kwargs):
        self._live_display = None
        super().__init__(*args, **kwargs)

    @classmethod
    def get_default_columns(cls) -> Tuple[ProgressColumn, ...]:
        return (
            SuccessSpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            SpinnerColumn(spinner_name="simpleDots", finished_text=""),
        )

    def get_renderables(self) -> Iterable[RenderableType]:
        yield from super().get_renderables()
        if self._live_display is not None:
            yield self._live_display

    @contextlib.contextmanager
    def enter_task(
        self,
        description,
        total=1,
        finished_description=None,
        exception_description="Task failed to excecute.",
        warn=False,
        hide=False,
    ):
        """Start and end a task in a progress bar."""
        task = self.add_task(description, total=total)
        exception = None
        try:
            yield task
        except Exception as e:
            finished_description = exception_description.format(exception=e)
            exception = e
            self.update(task_id=task, exception=True)
        finally:
            description = finished_description or self.tasks[task].description
            self.update(task_id=task, completed=total, description=description)
            if exception is not None and not hide:
                self.console.print_exception(show_locals=True)
            if exception is not None and not warn:
                exit(1)

    def live_display(self, renderable):
        """Display a renderable in a panel below the progress bar."""
        with self._lock:
            self._live_display = renderable
        self.refresh()


def tail(text, n=10):
    """Return the last n lines of a text string."""
    return "\n".join(text.splitlines()[-n:])

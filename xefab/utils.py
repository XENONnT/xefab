import contextlib
import errno
import os
import socket
from typing import Optional
import time
from types import TracebackType
from typing import Optional, Type, Union, List

from rich.console import Console, RenderableType
from rich.jupyter import JupyterMixin
from rich.live import Live
from rich.spinner import Spinner
from rich.style import StyleType
from rich.panel import Panel
from rich.layout import Layout
from rich import box
import pandas as pd
from invoke.util import enable_logging
from rich.table import Table


console = Console()


if os.environ.get("XEFAB_DEBUG") in ("1", "true", "True"):
    enable_logging()


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


class TaskLiveDisplay(JupyterMixin):
    
    def __init__(
        self,
        taskname: str,
        *,
        status: RenderableType = None,
        print_buffer: Union[str, List[str]] = None,
        log_buffer: Union[str, List[str]] = None,
        console: Optional[Console] = None,
        spinner: str = "dots",
        spinner_style: StyleType = "status.spinner",
        speed: float = 1.0,
        refresh_per_second: float = 12.5,
        transient: bool = False,
        show_log: bool = False,
        max_rows: int = 30, 
    ):
        
        self._taskname = taskname
        self._status = status
        self._log_buffer = log_buffer or []
        self._print_buffer = print_buffer or []
        self._show_log = show_log
        self._max_rows = max_rows
        self.spinner = spinner
        self.spinner_style = spinner_style
        self.speed = speed
        self._spinner = Spinner(spinner, text=self._status, style=self.spinner_style, speed=self.speed)
        
        self._live = Live(
            self,
            console=console,
            auto_refresh=True,
            refresh_per_second=refresh_per_second,
            transient=transient,
        )
    

    @property
    def show_log(self):
        return self._show_log
    
    @show_log.setter
    def show_log(self, value: bool):
        self._show_log = value
        
    def render(self):
        layout = Layout()
        layout.split_column(
            Layout(name="header"),
            Layout(name="output"),
            Layout(name="status"),
            )
        layout["output"].split_row(
            Layout(name="print"),
            Layout(name="log"),
            )
        layout.size = self._max_rows + 5
        layout["output"].size = self._max_rows
        layout["header"].size = 2
        layout["status"].size = 2
        layout["status"].visible = self._status is not None
        layout['output']['log'].visible = self.show_log

        header_panel = Panel("", subtitle=self._taskname, box=box.MINIMAL)
        print_panel = Panel('\n'.join(self._print_buffer)[:self._max_rows], title='Output', expand=True)
        log_panel = Panel('\n'.join(self._log_buffer)[:self._max_rows], title='Log', expand=True)
        
        layout['header'].update(header_panel)
        layout['output']['print'].update(print_panel)
        layout['output']['log'].update(log_panel)
        if self._status is not None:
            self._spinner.update(text=self._status)
            layout['status'].update(self._spinner)
        else:
            layout['status'].update("")
        return layout
    
    def status(self, value: RenderableType):
        self._status = value

    def log(self, *args):
        self._log_buffer.extend(map(str, args))
        
    def print(self, *args):
        self._print_buffer.extend(map(str, args))
        
    def start(self) -> None:
        """Start the status animation."""
        self._live.start()

    def stop(self) -> None:
        """Stop the spinner animation."""
        self._live.stop()

    def __rich__(self) -> RenderableType:
        return self.render()

    def __enter__(self) -> "Status":
        self.start()
        return self
    
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.stop()


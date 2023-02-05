import os
import contextlib
import errno
import socket
from typing import Optional

import pandas as pd
from rich.table import Table
from invoke.util import enable_logging


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

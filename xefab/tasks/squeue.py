import time

import pandas as pd
from fabric.connection import Connection
from fabric.tasks import task

from xefab.utils import console, df_to_table


def parse_squeue_output(squeue_output):
    """Parse the output of the squeue command."""

    squeue_output = squeue_output.split("\n")
    header, rows = squeue_output[0], squeue_output[1:]
    header_fields = header.split()
    squeue_data = []
    for row in rows:
        row_data = {}
        fields = row.split()
        for name, field in zip(header_fields, fields):
            row_data[name] = field
        squeue_data.append(row_data)
    return pd.DataFrame(squeue_data, columns=header_fields).dropna(how="all")


@task(aliases=["job-queue"])
def squeue(
    c: Connection, user: str = "me", partition: str = None, out: str = "", 
    hide: bool = False, warn: bool = False,
) -> pd.DataFrame:
    """Get the job-queue status."""

    command = 'squeue --format="%.18i %.9P %.30j %.8u %.8T %.10M %.9l %.6D %R"'

    if user in ["*", "all"]:
        pass
    elif user in ["me", "self", ""]:
        command += f" -u {c.user}"
    else:
        command += f" -u {user}"

    if partition:
        command += f" -p {partition}"

    
    r = c.run(command, hide=hide, warn=True)
    squeue_output = r.stdout
    if r.failed and not warn:
        console.print("Remote execution of squeue on {c.host} failed. stderr:")
        console.print(r.stderr)
        exit(r.return_code)

    df = parse_squeue_output(squeue_output)

    if out:
        with console.status(f"Saving squeue output to {out}..."):
            df.to_csv(out, index=False)
            time.sleep(0.5)
        console.print(f"Output written to {out}")
    if not hide:
        table = df_to_table(df)
        if len(df) > 10:
            with console.pager():
                console.print(table)
        else:
            console.print(table)
    return df

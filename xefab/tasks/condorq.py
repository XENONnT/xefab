import datetime

import pandas as pd
from fabric.tasks import task

from xefab.utils import console, df_to_table


@task(aliases=["job-queue"])
def condorq(c, all: bool = False, hide: bool = False):
    """Get the condor job queue."""
    cmd = "condor_q"
    if all:
        cmd += " -allusers"
    result = c.run(cmd, hide=True, warn=True)
    if result.failed:
        console.print(
            f"Remote execution of {cmd} on {c.host} failed. stderr: {result.stderr}"
        )
    df = parse_condorq_output(result.stdout)
    if not hide:
        table = df_to_table(df)
        console.print(table)
    return df


slots = {
    "OWNER": 1,
    "BATCH_NAME": 1,
    "SUBMITTED": 2,
    "DONE": 1,
    "RUN": 1,
    "IDLE": 1,
    "HOLD": 1,
    "TOTAL": 1,
    "JOB_IDS": 3,
}


mergers = {
    "SUBMITTED": lambda x: pd.to_datetime(
        f"{datetime.datetime.utcnow().year}/{x[0]}T{x[1]}"
    ),
    "JOB_IDS": lambda x: "".join(x),
}


def parse_row(line, columns):
    parts = line.split()
    row = {}
    for column in columns:
        value = [parts.pop(0) for _ in range(slots[column])]
        merger = mergers.get(column, lambda x: x[0])
        row[column] = merger(value)

    return row


def parse_condorq_output(condorq_output):
    lines = condorq_output.split("\n")
    rows = []
    columns = []
    for line in lines:
        if line.startswith("OWNER"):
            columns = line.split()
            continue

        if not columns:
            continue

        if not line:
            break

        row = parse_row(line, columns)
        rows.append(row)

    df = pd.DataFrame(rows, columns=columns).dropna(how="all")
    return df

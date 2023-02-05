import time
import pandas as pd
from fabric.connection import Connection
from fabric.tasks import task
from xefab.utils import df_to_table


def parse_squeue_output(squeue_output):
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


@task
def squeue(c: Connection, 
        user: str = 'me', partition: str = None, 
        out: str = '') -> pd.DataFrame:
    
    """Get the job-queue status.
    """

    command = "squeue"

    if user in ['*', 'all']:
        pass
    elif user in ['me', 'self', '']:
        command += f" -u {c.user}"
    else:
        command += f" -u {user}"
    
    if partition:
        command += f" -p {partition}"

    with c.console.status(f"Running {command} on {c.host}..."):
        r = c.run(command, hide=True, warn=True)
        squeue_output = r.stdout
    if r.failed:
        c.console.print("Remote execution of squeue on {c.host} failed. stderr:")
        c.console.print(r.stderr)
        exit(r.return_code)

    df = parse_squeue_output(squeue_output)

    if out:
        with c.console.status(f"Saving squeue output to {out}..."):
            df.to_csv(out, index=False)
            time.sleep(0.5)
        c.console.print(f"Output written to {out}")
    else:
        table = df_to_table(df)
        if len(df) > 10:
            with c.console.pager():
                c.console.print(table)
        else:
            c.console.print(table)

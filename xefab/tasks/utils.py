from fabric.tasks import task
from xefab.utils import console
from invoke.context import DataProxy


def printable(d):
    if isinstance(d, (dict, DataProxy)):
        return {k: printable(v) for k, v in d.items()}
    elif isinstance(d, type):
        return d.__qualname__
    return d


@task
def show_context(c, config_name: str = None):
    """Show the context being used for tasks."""
    if config_name is None:
        console.print_json(data=printable(c), indent=4)
        return
    result = getattr(c, config_name, None)
    if result is None:
        result = c.get(config_name, None)
    if result is None:
        console.print(f"Config {config_name} not found.")
    result = printable(result)
    if isinstance(result, dict):
        console.print_json(data=result, indent=4)
    else:
        console.print(f"{config_name}: {result}")

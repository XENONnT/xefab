from fabric.connection import Connection
from fabric.tasks import task
from invoke.context import DataProxy

from xefab.collection import XefabCollection
from xefab.utils import console

from . import admin, github, install, secrets, shell

namespace = XefabCollection("root")

install = XefabCollection.from_module(install, name="install")
namespace.add_collection(install)

secret = XefabCollection.from_module(secrets, name="secrets")
namespace.add_collection(secret)

admin = XefabCollection.from_module(admin, name="admin")
namespace.add_collection(admin)

github = XefabCollection.from_module(github, name="github")
namespace.add_collection(github)

sh = XefabCollection.from_module(shell, name="sh")
namespace.add_collection(sh)


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


namespace.add_task(show_context)

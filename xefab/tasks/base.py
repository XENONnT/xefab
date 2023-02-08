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


@task
def which(c, command: str, bash_profile: bool = False, hide: bool = False):
    cmd = f"which {command}"
    if bash_profile and file_exists(c, f"/home/{c.user}/.bash_profile", hide=True):
        cmd = f"source /home/{c.user}/.bash_profile && which {command}"
    result = c.run(cmd, hide=True, warn=True)
    if not hide:
        msg = result.stdout.strip() if result.ok else f"{command} is not in path."
        console.print(msg)
    return result.stdout.strip() if result.ok else None


@task
def file_exists(c, path: str, hide: bool = False):
    result = c.run(f"test -f {path}", hide=True, warn=True)
    if not hide:
        msg = "1" if result.ok else "0"
        console.print(msg)
    return result.ok


@task
def directory_exists(c, path: str, hide: bool = False):
    result = c.run(f"test -d {path}", hide=True, warn=True)
    if not hide:
        msg = "1" if result.ok else "0"
        console.print(msg)
    return result.ok


@task
def get_system(c, hide=False):
    result = c.run("python -m platform", hide=True, warn=True)
    assert result.ok, "Failed to deduce system."
    system = result.stdout.split("-")[0]
    if not hide:
        console.print(f"System: {system}")
    return system


@task
def path(
    c,
    bash_profile: bool = False,
    bashrc: bool = False,
    zshrc: bool = False,
    fishrc: bool = False,
    hide: bool = False,
):
    assert not (
        (bashrc or bash_profile) and zshrc and fishrc
    ), "Only one of bashrc, zshrc, or fishrc can be True."
    cmd = "echo $PATH"
    if bashrc and file_exists(c, f"/home/{c.user}/.bashrc", hide=True):
        cmd = f"source /home/{c.user}/.bashrc && echo $PATH"
        result = c.run(cmd, hide=True, warn=True, pty=True, shell="/bin/bash")
    elif zshrc and file_exists(c, f"/home/{c.user}/.zshrc", hide=True):
        cmd = f"source /home/{c.user}/.zshrc && echo $PATH"
        result = c.run(cmd, hide=True, warn=True, pty=True, shell="/bin/zsh")
    elif fishrc and file_exists(
        c, f"/home/{c.user}/.config/fish/config.fish", hide=True
    ):
        cmd = f"source /home/{c.user}/.config/fish/config.fish && echo $PATH"
        result = c.run(cmd, hide=True, warn=True, pty=True, shell="/bin/fish")

    if bash_profile and file_exists(c, f"/home/{c.user}/.bash_profile", hide=True):
        cmd = f"source /home/{c.user}/.bash_profile && {cmd}"
        result = c.run(cmd, hide=True, warn=True, pty=True, shell="/bin/bash")

    assert (
        result.ok
    ), f"Failed to print path. stdout: {result.stdout} \n stderr: {result.stderr}"
    if not hide:
        console.print(result.stdout.strip())
    return result.stdout.strip()

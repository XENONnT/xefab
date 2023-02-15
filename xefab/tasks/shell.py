from fabric.connection import Connection
from fabric.tasks import task

from xefab.utils import console

SHELL_PROFILE_FILES = {
    "sh": ["~/.profile"],
    "bash": ["~/.profile", "~/.bash_profile"],
    "zsh": ["~/.profile", "~/.zprofile"],
}


@task(default=True)
def shell(c: Connection, shell: str = None):
    """Open interactive shell on remote host."""

    if shell is None:
        shell = c.config.run.shell
    if isinstance(c, Connection):
        c.shell()
    else:
        while True:
            try:
                cmd = input(f"{shell}:~$ ")
                if cmd == "exit":
                    break
                c.run(cmd, shell=shell)
            except KeyboardInterrupt:
                break


@task
def is_file(c, path: str, local: bool = False, hide: bool = False):
    """Check if a file exists."""

    cmd = f"test -f {path}"
    if local:
        result = c.local(cmd, hide=True, warn=True)
    else:
        result = c.run(cmd, hide=True, warn=True)
    if not hide:
        msg = "1" if result.ok else "0"
        console.print(msg)
    return result.ok


@task
def is_dir(c, path: str, local: bool = False, hide: bool = False):
    """Check if a directory exists."""

    cmd = f"test -d {path}"
    if local:
        result = c.local(cmd, hide=True, warn=True)
    else:
        result = c.run(cmd, hide=True, warn=True)
    if not hide:
        msg = "1" if result.ok else "0"
        console.print(msg)
    return result.ok


@task
def exists(c, path: str, local: bool = False, hide: bool = False):
    """Check if a file or directory exists."""

    cmd = f"test -e {path}"
    if local:
        result = c.local(cmd, hide=hide, warn=True)
    else:
        result = c.run(cmd, hide=hide, warn=True)
    if not hide:
        msg = "1" if result.ok else "0"
        console.print(msg)
    return result.ok


@task
def which(
    c,
    command: str,
    local: bool = False,
    no_user_profile: bool = False,
    no_system_profile: bool = False,
    shell: str = None,
    hide: bool = False,
):
    """Find the path to a command on the remote host."""

    if shell is None:
        shell = "bash"

    cmd = f"which {command}"

    if not no_system_profile and is_file(c, f"/etc/profile", local=local, hide=True):
        cmd = f"source /etc/profile && {cmd}"
    if not no_user_profile:
        for f in SHELL_PROFILE_FILES.get(shell):
            fpath = f.replace("~/", f"/home/{c.user}/")
            if is_file(c, fpath, local=local, hide=True):
                cmd = f"source {fpath} && {cmd}"

    if local and isinstance(c, Connection):
        result = c.local(cmd, hide=True, warn=True, shell=f"/bin/{shell}")
    else:
        result = c.run(cmd, hide=True, warn=True, shell=f"/bin/{shell}")

    if not hide:
        msg = result.stdout.strip() if result.ok else ""
        console.print(msg)
    return result.stdout.strip() if result.ok else None


@task
def get_system(c, hide=False):
    """Deduce the system type of the remote host."""

    result = c.run("python -m platform", hide=True, warn=True)
    assert result.ok, "Failed to deduce system."
    system = result.stdout.split("-")[0]
    if not hide:
        console.print(f"System: {system}")
    return system


@task
def path(
    c,
    profile: bool = False,
    shell: str = None,
    local: bool = False,
    hide: bool = False,
):
    """Print the PATH variable on the remote host."""

    if shell is None:
        shell = "bash"

    cmd = "echo $PATH"

    if local and isinstance(c, Connection):
        result = c.local(cmd, hide=True, warn=True, shell=f"/bin/{shell}")
    else:
        if profile:
            if is_file(c, f"/etc/profile", hide=True):
                cmd = f"source /etc/profile && {cmd}"
            for f in SHELL_PROFILE_FILES.get(shell):
                if is_file(c, f, hide=True):
                    fpath = f.replace("~/", f"/home/{c.user}/")
                    cmd = f"source {fpath} && {cmd}"

        result = c.run(cmd, hide=True, warn=True, shell=f"/bin/{shell}")
    assert (
        result.ok
    ), f"Failed to print path. stdout: {result.stdout} \n stderr: {result.stderr}"
    if not hide:
        console.print(result.stdout.strip())
    return result.stdout.strip()

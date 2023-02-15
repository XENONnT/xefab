import json
from typing import Callable, Optional

from fabric.tasks import task

from xefab.utils import console

from .shell import get_system, which

CONDA_LINKS = {
    "linux": "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh",
    "darwin": "https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh",
    "windows": "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe",
}


def ensure_dependency(dep, local: bool = False, installer: Optional[Callable] = None):
    @task
    def wrapper(c, *args, **kwargs):
        if which(c, dep, local=local, hide=True):
            return
        if installer is not None:
            installer(c, *args, **kwargs)
        else:
            raise RuntimeError(f"Dependency {dep} not found.")

    return wrapper


@task
def go(c, force: bool = False):
    """Install Go."""

    if which(c, "go", hide=True) and not force:
        console.print("Go already installed on system.")
        return

    system = get_system(c, hide=True)
    if get_system(c, hide=True) in ("Linux", "Darwin"):
        c.run(
            "wget -q -O - https://raw.githubusercontent.com/canha/golang-tools-install-script/master/goinstall.sh | bash"
        )
        console.print(
            "Go installed. Please add `export PATH=$PATH:/usr/local/go/bin` to your .bashrc/.profile file"
        )
    else:
        raise RuntimeError(f"{system} currently not supported by this task.")


@task
def gopass(c, force: bool = False):
    """Install gopass."""

    if which(c, "gopass", hide=True) and not force:
        console.print("Gopass already installed on system.")
        return
    c.run("go install github.com/gopasspw/gopass@latest")
    console.print("Done")


@task
def chezmoi(c, force: bool = False):
    """Install chezmoi."""

    if which(c, "chezmoi", hide=True) and not force:
        console.print("Chezmoi already installed on system.")
        return
    c.run('sh -c "$(curl -fsLS get.chezmoi.io)"')
    console.print("Done.")


@task(aliases=["gh"])
def github_cli(c, force: bool = False):
    """Install the Github CLI."""

    console.print("Checking for existing installation.")
    have_gh = which(c, "gh", hide=True)

    if have_gh and not force:
        console.print("Github CLI already installed on system.")
        return

    console.print("Attempting to install Github CLI.")

    if which(c, "conda", hide=True):
        console.print("Installing Github CLI via conda.")
        c.run("conda install gh --channel conda-forge")
        return

    console.print("Finding latest release.")

    command = f"gh api /repos/cli/cli/releases/latest"
    if hasattr(c, "local"):
        result = c.local(command, hide=True, warn=True)
    else:
        result = c.run(command, hide=True, warn=True)
    assert result.ok, "Failed to get latest release."
    latest_release = json.loads(result.stdout)
    console.print(f"Installing release: {latest_release['tag_name']}")
    assets = latest_release["assets"]

    system = get_system(c, hide=True)

    if system == "Linux":
        asset = [a for a in assets if a["name"].endswith("linux_amd64.tar.gz")][0]
    elif system == "Darwin":
        asset = [a for a in assets if a["name"].endswith("darwin_amd64.tar.gz")][0]
    else:
        raise RuntimeError(f"{system} currently not supported by this task.")

    console.print(
        f"Downloading asset: {asset['name']} from {asset['browser_download_url']}"
    )
    c.run(f"wget -q {asset['browser_download_url']}")

    c.run(f"tar -xzf {asset['name']}")

    c.run(
        f"mv {asset['name'].replace('.tar.gz', '')}/bin/gh /home/{c.user}/.local/bin/gh"
    )
    console.print(
        f"gh installed. Please ensure `/home/{c.user}/.local/bin` is in your path."
    )
    console.print("Done.")


@task(
    aliases=["gpg"],
)
def gnupg(c, force: bool = False):
    """Install GnuPG."""

    if which(c, "gpg", hide=True) and not force:
        console.print("GnuPG already installed on system.")
        return
    scripts = {
        "install_gpg_all.sh": "https://raw.githubusercontent.com/rnpgp/gpg-build-scripts/master/install_gpg_all.sh",
        "install_gpg_component.sh": "https://raw.githubusercontent.com/rnpgp/gpg-build-scripts/master/install_gpg_component.sh",
    }

    for name, script in scripts.items():
        c.run(f"wget -q {script}")
        c.run(f"chmod +x {name}")
    c.run("./install_gpg_all.sh")
    console.print("Done.")


@task(
    aliases=["conda"],
)
def miniconda(c, download_only: bool = False):
    """Install Miniconda."""

    system = get_system(c, hide=True).lower()
    if system not in CONDA_LINKS:
        raise RuntimeError(f"{system} currently not supported by this task.")
    link = CONDA_LINKS[system]
    with console.status(f"Downloading miniconda installer from {link}"):
        result = c.run(f"wget -q {link}", hide=True, warn=True)
    if result.failed:
        raise RuntimeError(f"Failed to download miniconda installer.")

    if download_only:
        console.print(f"Miniconda installer downloaded.")
        return

    if system == "windows":
        command = """start /wait "" Miniconda3-latest-Windows-x86_64.exe /InstallationType=JustMe /RegisterPython=0 /S /D=%UserProfile%\Miniconda3
        """
        c.run(command)
        return
    elif system == "darwin":
        c.run(f"chmod +x Miniconda3-latest-MacOSX-x86_64.sh")
        c.run(f"./Miniconda3-latest-MacOSX-x86_64.sh")
    elif system == "linux":
        c.run(f"chmod +x Miniconda3-latest-Linux-x86_64.sh")
        c.run(f"./Miniconda3-latest-Linux-x86_64.sh  -b -p $HOME/miniconda")
    console.print("Done.")

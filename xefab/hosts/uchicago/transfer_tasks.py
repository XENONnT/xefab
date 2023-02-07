from fabric.tasks import task

from xefab.utils import console


@task
def download_file(c, path: str, out: str = None, preserve_mode: bool = True):
    """Download a file from a remote server."""
    with console.status(f'Downloading {path} from {c.host}'):
        c.get(path, local=out, preserve_mode=preserve_mode)
    console.print(f"Done.")


@task
def upload_file(c, path: str, remote_path: str = None, preserve_mode: bool = True):
    """Upload a file to a remote server."""
    with console.status(f'Uploading {path} to {c.host}'):
        c.put(path, remote=remote_path, preserve_mode=preserve_mode)
    console.print(f"Done.")

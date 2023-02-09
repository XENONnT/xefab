import json
import tempfile

from fabric.connection import Connection
from fabric.tasks import task

from xefab.utils import console, try_local

from .admin import add_recipient
from .install import ensure_dependency, github_cli
from .shell import which


def github_api_call(
    c,
    path: str,
    method: str = "GET",
    raw: bool = False,
    hide: bool = False,
    pages: int = 10,
    per_page=50,
):
    promises = []
    for page in range(1, pages + 1):
        cmd = f"gh api {path}?page={page}&per_page={per_page}"
        if method != "GET":
            cmd += f" -X {method}"

        promise = c.run(cmd, hide=True, warn=True, asynchronous=True)
        promises.append(promise)

    for promise in promises:
        result = promise.join()
        if result.failed:
            raise RuntimeError(f"Failed to get github keys: {result.stderr}")

        data = result.stdout
        if data == "[]":
            continue
        if raw:
            yield data
        else:
            yield from json.loads(data)


@task
def is_public(c, repo: str, owner: str = "XENONnT"):
    for doc in github_api_call(c, f"/users/{owner}/repos", hide=True):
        if doc["name"] == repo:
            return not doc["private"]
    return False


@task
def is_private(c, repo: str, owner: str = "XENONnT"):
    for doc in github_api_call(c, f"/users/{owner}/repos", hide=True):
        if doc["name"] == repo:
            return doc["private"]
    return True


@task
@try_local
def token(c):
    result = c.run(f"gh auth token", hide=True, warn=True)
    if result.failed:
        raise RuntimeError(f"Failed to get github token: {result.stderr}")

    token = result.stdout.strip()
    console.print(token)
    return token


@task(pre=[ensure_dependency("gh", installer=github_cli)])
def xenonnt_members(c, hide: bool = False):
    users = github_api_call(c, "orgs/XENONnT/members", hide=True)

    usernames = [user["login"] for user in users]
    if not hide:
        console.print(usernames)
        console.print(f"Found {len(usernames)} members.")
    return usernames


@task(pre=[ensure_dependency("gh", installer=github_cli)])
def xenon1t_members(c, hide: bool = False):
    users = github_api_call(c, "orgs/XENON1T/members", hide=True)

    usernames = [user["login"] for user in users]
    if not hide:
        console.print(usernames)
        console.print(f"Found {len(usernames)} members.")
    return usernames


@task(pre=[ensure_dependency("gh", installer=github_cli)])
def xenonnt_keys(c, hide: bool = False, add: bool = False):
    users = github_api_call(c, "orgs/XENONnT/members", hide=True)

    keys = []
    for user in users:
        username = user["login"]
        keys = github_api_call(c, f"users/{username}/gpg_keys", hide=True, pages=1)
        keys = [key for key in keys if key["can_encrypt_storage"] and key["raw_key"]]
        if not keys:
            continue
        keys.extend(keys)
        if not hide:
            console.print(f"Found {len(keys)} keys for {username}:")
            for key in keys:
                console.print(key["key_id"])
        if add:
            for key in keys:
                add_recipient(c, key)
    if add:
        c.run("gopass sync", warn=True)
    return keys


@task
def clone(c, repo: str, org="XENONnT", branch: str = "master", dest: str = None):
    if dest is None:
        dest = repo
    repo = f"{org}/{repo}"
    if isinstance(c, Connection) and which(c, "gh", local=True, hide=True):
        with tempfile.TemporaryDirectory() as tmpdir:
            c.local(f"gh repo clone {repo} {tmpdir}")
            c.put(tmpdir, remote=dest)
    elif which(c, "gh", hide=True):
        c.run(f"gh repo clone {repo} {dest}")
    else:
        c.run(f"git clone git@github.com:{org}/{repo}.git {dest}")
    console.print(f"Cloned {repo} to {dest}.")

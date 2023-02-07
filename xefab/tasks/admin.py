import json
from io import StringIO, BytesIO
from fabric.tasks import task
from xefab.utils import console
import pandas as pd
from .install import ensure_dependency, github_cli
from .secrets import github_token


def github_api_call(c, path: str, 
                    method: str = "GET", 
                    raw: bool = False, 
                    hide: bool = False,
                    pages: int = 10,
                    per_page=50):
    promises = []
    for page in range(1, pages+1):
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
        if data == '[]':
            continue
        if raw:
            yield data
        else:
            yield from json.loads(data)


def add_recipient(c, key: dict, gnuhome: str = "~/.gnupg", gopass_store: str = "xenonnt"):
    import gnupg
    gpg = gnupg.GPG(homedir=gnuhome)
    gpg.import_keys(key['raw_key'])
    console.print(f"Added {key['key_id']} to {gnuhome}")
    result = c.run(f"gopass --yes recipients add --store {gopass_store} {key['key_id']}", hide=True, warn=True)
    if result.ok:
        console.print(f"Added {key['key_id']} to gopass")
    else:
        console.print(f"Failed to add {key['key_id']} to gopass: {result.stderr}")

@task(pre=[ensure_dependency('gh', installer=github_cli)])
def list_xenonnt_members(c, hide: bool = False):
    users = github_api_call(c, "orgs/XENONnT/members", hide=True)
    
    usernames = [user["login"] for user in users]
    if not hide:
        console.print(usernames)
        console.print(f'Found {len(usernames)} members.')
    return usernames


@task(pre=[ensure_dependency('gh', installer=github_cli)])
def list_xenon1t_members(c, hide: bool = False):
    users = github_api_call(c, "orgs/XENON1T/members", hide=True)
    
    usernames = [user["login"] for user in users]
    if not hide:
        console.print(usernames)
        console.print(f'Found {len(usernames)} members.')
    return usernames


@task(pre=[ensure_dependency('gh', installer=github_cli)])
def get_xenonnt_keys(c, hide: bool = False, add: bool = False):
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
            console.print(f'Found {len(keys)} keys for {username}:')
            for key in keys:
                console.print(key["key_id"])
        if add:
            for key in keys:
                add_recipient(c, key)
    if add:
        c.run("gopass sync", warn=True)
    return keys


@task
def user_db(c, limit: int = None, hide: bool = False):
    users = c.config.xent_collection(collection='users').find({}, projection={'_id': 0})
    if limit is not None:
        users = users.limit(int(limit))
    df = pd.json_normalize(list(users))
    if not hide:
        console.print_json(df.to_json(orient='records'), indent=4)
    return df

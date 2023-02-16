import pandas as pd
from fabric.tasks import task

from xefab.utils import console


def add_recipient(
    c, key: dict, gnuhome: str = "~/.gnupg", gopass_store: str = "xenonnt"
):
    """Add a recipient to the gopass store."""
    import gnupg

    gpg = gnupg.GPG(homedir=gnuhome)
    gpg.import_keys(key["raw_key"])
    console.print(f"Added {key['key_id']} to {gnuhome}")
    result = c.run(
        f"gopass --yes recipients add --store {gopass_store} {key['key_id']}",
        hide=True,
        warn=True,
    )
    if result.ok:
        console.print(f"Added {key['key_id']} to gopass")
    else:
        console.print(f"Failed to add {key['key_id']} to gopass: {result.stderr}")


@task
def user_db(c, limit: int = None, hide: bool = False):
    """Get all users from the user database."""
    users = c.config.xent_collection(collection="users").find({}, projection={"_id": 0})
    if limit is not None:
        users = users.limit(int(limit))
    df = pd.json_normalize(list(users))
    if not hide:
        console.print_json(df.to_json(orient="records"), indent=4)
    return df

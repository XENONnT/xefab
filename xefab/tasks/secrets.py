
from fabric.tasks import task
from xefab.collection import XefabCollection
from xefab.utils import console

from .install import ensure_dependency, gopass, chezmoi


namespace = XefabCollection('secrets')


@task(pre=[ensure_dependency('gopass', installer=gopass)])
def setup(c, name: str = None, email: str = None,
            repo_url: str = 'github.com/XENONnT/secrets'):
    if name is None:
        name = console.input('Your name: ')
    if email is None:
        email = console.input('Your email (Used in github account): ')
    cmd = ('gopass'
        ' --yes setup'
        f' --remote {repo_url}'
        ' --alias xenonnt'
        f' --name {name}'
        f' --email {email}')
    c.run(cmd)
namespace.add_task(setup)


@task
def github_token(c):
    result = c.run(f'gh auth token', hide=True, warn=True)
    if result.failed:
        raise RuntimeError(f"Failed to get github token: {result.stderr}")

    token = result.stdout.strip()
    console.print(token)
    return token
namespace.add_task(github_token)


@task(ensure_dependency('chezmoi', installer=chezmoi))
def setup_utilix_config(c, apply: bool = False):
    command = 'chezmoi init https://github.com/XENONnT/dotfiles.git'
    result = c.run(command, hide=False, warn=True)
    if result.failed:
        raise RuntimeError(f"Failed to init chezmoi: {result.stderr}")

    result = c.run('chezmoi diff --no-pager ~/.xenon_config')
    if result.failed:
        raise RuntimeError(f"Failed to diff chezmoi: {result.stderr}")
    if not result.stdout:
        console.print('No changes to apply.')
        return
    console.print('Changes to apply:')
    console.print(result.stdout)
    if apply:
        c.run('chezmoi apply')
namespace.add_task(setup_utilix_config)


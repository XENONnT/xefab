from fabric.tasks import task
from xefab.utils import console


def in_path(c, command: str):
    result = c.run(f"which {command}", hide=True, warn=True)
    return result.ok


def ensure_dependency(dep, installer=None):
    @task
    def wrapper(c, *args, **kwargs):
        if in_path(c, dep):
            return
        if installer is not None:
            installer(c, *args, **kwargs)
        else:
            raise RuntimeError(f"Dependency {dep} not found.")
    return wrapper

@task(pre=[ensure_dependency('wget')])
def go(c, force: bool = False):
    if in_path(c, 'go') and not force:
        console.print('Go already installed on system.')
        return
    result = c.run('python -m platform', hide=True, warn=True)
    assert result.ok, "Failed to deduce system."
    system = result.stdout.split('-')[0]
    if system in ('Linux', 'Darwin'):
        c.run('wget -q -O - https://raw.githubusercontent.com/canha/golang-tools-install-script/master/goinstall.sh | bash')
        console.print('Go installed. Please add `export PATH=$PATH:/usr/local/go/bin` to your .bashrc/.profile file')
    else:
        raise RuntimeError(f"{system} currently not supported by this task.")


@task(pre=[ensure_dependency('go', installer=go)])
def gopass(c, force: bool = False):
    if in_path(c, 'gopass') and not force:
        console.print('Gopass already installed on system.')
        return
    c.run('go install github.com/gopasspw/gopass@latest')
    console.print('Done')


@task
def chezmoi(c, force: bool = False):
    if in_path(c, 'chezmoi') and not force:
        console.print('Chezmoi already installed on system.')
        return
    c.run('sh -c "$(curl -fsLS get.chezmoi.io)"')
    console.print('Done.')


@task
def github_cli(c, force: bool = False):
    if in_path(c, 'gh') and not force:
        console.print('Github CLI already installed on system.')
        return
    c.run('conda install gh --channel conda-forge')
    console.print('Done.')


@task(pre=[ensure_dependency('wget')])
def gnupg(c, force: bool = False):
    if in_path(c, 'gpg') and not force:
        console.print('GnuPG already installed on system.')
        return
    scripts = {
        'install_gpg_all.sh': 'https://raw.githubusercontent.com/rnpgp/gpg-build-scripts/master/install_gpg_all.sh',
        'install_gpg_component.sh': 'https://raw.githubusercontent.com/rnpgp/gpg-build-scripts/master/install_gpg_component.sh'
    }
        
    for name, script in scripts.items():
        c.run(f'wget -q {script}')
        c.run(f'chmod +x {name}')
    c.run('./install_gpg_all.sh')
    console.print('Done.')
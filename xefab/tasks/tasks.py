
from fabric.tasks import task

@task
def echo(c, message: str):
    c.console.print(message)
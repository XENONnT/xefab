from fabric.tasks import task

from xefab.collection import XefabCollection

namespace = XefabCollection("osg")

namespace.configure({"hostnames": "login.xenon.ci-connect.net"})


@task
def condor_q(c):
    result = c.run("condor_q", hide=True, warn=True)
    if result.ok:
        c.console.print(result.stdout)


namespace.add_task(condor_q)

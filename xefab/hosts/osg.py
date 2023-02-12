from xefab.collection import XefabCollection
from xefab.tasks.condorq import condorq

namespace = XefabCollection("osg")

namespace.configure({"hostnames": "login.xenon.ci-connect.net"})

namespace.add_task(condorq)

from xefab.collection import XefabCollection
from .condorq_task import condorq

namespace = XefabCollection("osg")

namespace.configure({"hostnames": "login.xenon.ci-connect.net"})

namespace.add_task(condorq)

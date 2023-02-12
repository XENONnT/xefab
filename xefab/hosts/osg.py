from xefab.collection import XefabCollection
from xefab.tasks.condorq import condorq
from xefab.tasks.mc_chain import mc_chain

namespace = XefabCollection("osg")

namespace.configure({"hostnames": "login.xenon.ci-connect.net"})

namespace.add_task(condorq)
namespace.add_task(mc_chain)


from .squeue_task import squeue
from .jupyter_task import start_jupyter

from xefab.collection import XefabCollection

namespace = XefabCollection('dali')

namespace.configure({'hostname': 'dali-login2.rcc.uchicago.edu'})

namespace.add_task(squeue)
namespace.add_task(start_jupyter)

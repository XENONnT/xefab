from .squeue_task import squeue
from .jupyter_task import start_jupyter
from xefab.collection import XefabCollection

namespace = XefabCollection('midway')

namespace.configure({'hostname': 'midway2.rcc.uchicago.edu'})

namespace.add_task(squeue)
namespace.add_task(start_jupyter)
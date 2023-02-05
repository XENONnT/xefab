from xefab.collection import XefabCollection

from .jupyter_task import start_jupyter
from .squeue_task import squeue

namespace = XefabCollection("midway")

namespace.configure(
    {"hostnames": ["midway2.rcc.uchicago.edu", "midway1.rcc.uchicago.edu"]}
)

namespace.add_task(squeue)
namespace.add_task(start_jupyter)

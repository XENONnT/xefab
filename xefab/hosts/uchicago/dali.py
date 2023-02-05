from xefab.collection import XefabCollection

from .jupyter_task import start_jupyter
from .squeue_task import squeue

namespace = XefabCollection("dali")

namespace.configure(
    {"hostnames": ["dali-login2.rcc.uchicago.edu", "dali-login1.rcc.uchicago.edu"]}
)

namespace.add_task(squeue)
namespace.add_task(start_jupyter)

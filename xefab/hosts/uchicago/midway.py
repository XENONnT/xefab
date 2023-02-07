from xefab.collection import XefabCollection

from .jupyter_task import start_jupyter
from .squeue_task import squeue
from .transfer_tasks import download_file, upload_file
from .batchq import submit_job


namespace = XefabCollection("midway")

namespace.configure(
    {"hostnames": ["midway2.rcc.uchicago.edu", 
                "midway2-login1.rcc.uchicago.edu", 
                "midway2-login2.rcc.uchicago.edu"]}
)

namespace.add_task(squeue)
namespace.add_task(start_jupyter)
namespace.add_task(download_file)
namespace.add_task(upload_file)
namespace.add_task(submit_job)

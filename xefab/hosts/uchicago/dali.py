from xefab.collection import XefabCollection
from xefab.tasks import utils
from .jupyter_task import start_jupyter
from .squeue_task import squeue
from .transfer_tasks import download_file, upload_file
from .batchq import submit_job

namespace = XefabCollection("dali")

namespace.configure(
    {"hostnames": ["dali-login2.rcc.uchicago.edu", "dali-login1.rcc.uchicago.edu"]}
)

namespace.add_task(squeue)
namespace.add_task(start_jupyter)
namespace.add_task(download_file)
namespace.add_task(upload_file)
namespace.add_task(submit_job)
namespace.add_task(utils.show_context)

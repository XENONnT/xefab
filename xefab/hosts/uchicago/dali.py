from xefab.collection import XefabCollection
from xefab.tasks.base import show_context
from xefab.tasks.batchq import submit_job
from xefab.tasks.jupyter_task import start_jupyter
from xefab.tasks.squeue_task import squeue
from xefab.tasks.transfer_tasks import download_file, upload_file

namespace = XefabCollection("dali")

namespace.configure(
    {"hostnames": ["dali-login2.rcc.uchicago.edu", "dali-login1.rcc.uchicago.edu"]}
)

namespace.add_task(squeue)
namespace.add_task(start_jupyter)
namespace.add_task(download_file)
namespace.add_task(upload_file)
namespace.add_task(submit_job)
namespace.add_task(show_context)

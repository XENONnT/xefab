from xefab.collection import XefabCollection
from xefab.tasks.batchq import sbatch
from xefab.tasks.jupyter import start_jupyter
from xefab.tasks.main import show_context
from xefab.tasks.squeue import squeue
from xefab.tasks.transfer import download_file, upload_file

namespace = XefabCollection("dali")

namespace.configure(
    {"hostnames": ["dali-login2.rcc.uchicago.edu", "dali-login1.rcc.uchicago.edu"]}
)

namespace.add_task(squeue)
namespace.add_task(start_jupyter)
namespace.add_task(download_file)
namespace.add_task(upload_file)
namespace.add_task(sbatch)
namespace.add_task(show_context)

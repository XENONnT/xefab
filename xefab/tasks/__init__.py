
from invoke.collection import Collection

from . import tasks

namespace = Collection.from_module(tasks)


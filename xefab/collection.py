from paramiko.config import SSHConfig
from invoke.collection import Collection
from invoke.tasks import Task
from invoke.config import merge_dicts
from invoke.util import debug

from .entrypoints import get_entry_points


class XefabCollection(Collection):
    """Collection that assigns host name
    as default for all its tasks.
    """
    entrypoint_prefix = 'xefab.tasks'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.name is not None:
            self.load_objects_from_entry_points(self.name)

    def task_with_config(self, name):
        # fetch the task object
        task, conf = super().task_with_config(name)

        # set default hosts for task
        if 'hostname' in self.configuration():
            task.hosts = [self.name]
        return task, conf

    def load_objects_from_entry_points(self, group):
        """Load tasks/collections from entry points.
        """
        if not group.startswith(self.entrypoint_prefix):
            group = f'{self.entrypoint_prefix}.{group}'

        for ep in get_entry_points(group):
            try:
                obj = ep.load()
                if isinstance(obj, type):
                    obj = obj()
                self._add_object(obj, name=ep.name)
            except TypeError as e:
                debug(f"xefab.{self.name}: Error loading tasks from {ep.name} due to wrong type. "
                      f"details: {e}")
                continue
            except ImportError as e:
                debug(f"xefab.{self.name}: Error loading tasks from {ep.name} due to import error."
                      f"details: {e}")
                continue
            except Exception as e:
                debug(f"xefab.{self.name}: Error loading tasks from {ep.name} due to unknwon error."
                     f"details: {e}")
                continue

        

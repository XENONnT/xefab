import contextlib
import io
import os
from pathlib import Path

from fabric.connection import Connection
from invoke.context import Context
from pydantic import BaseModel, root_validator

from .utils import console, filesystem


class TemplateFile(BaseModel):
    """
    A template file that can be rendered using a pydantic model.
    The model should contain a __TEMPLATE__ attribute that is a
    string containing the template or a path to a file.
    All fields in the model will be available to the template.
    """

    __NAME__: str = None
    __TEMPLATE__: str = None

    @classmethod
    def get_template(cls):
        path = Path(cls.__TEMPLATE__)
        if path.is_file():
            return path.read_text()
        else:
            return cls.__TEMPLATE__

    @root_validator
    def format_args(cls, values):
        for name, field in cls.__fields__.items():
            value = values.get(name, field.default)
            if isinstance(value, str):
                values[name] = value.format(**values)
        return values

    def __init_subclass__(cls):
        if cls.__TEMPLATE__ is None or not cls.__TEMPLATE__.strip():
            raise TypeError(
                "Template class must have a non-empty __TEMPLATE__ attribute defined"
            )
        if cls.__NAME__ is None or not cls.__NAME__.strip():
            raise TypeError(
                "Template class must have a non-empty __NAME__ attribute defined"
            )

    @property
    def content(self):
        template = self.get_template()
        kwargs = self.dict()
        return template.format(**kwargs)

    @contextlib.contextmanager
    def open(self, mode="r"):
        if mode == "r":
            yield io.StringIO(self.content)
        elif mode == "rb":
            yield io.BytesIO(self.content.encode())
        else:
            raise RuntimeError("File is not writable")

    def deploy(self, c: Context, path, hide=False, warn=False):
        try:
            fs = filesystem(c)
            fs.makedirs(path, exist_ok=True)
            full_path = fs.sep.join([path, self.__NAME__])
            fs.write_text(full_path, self.content)
        except Exception as e:
            if not warn:
                raise e
            if not hide:
                console.print_exception(show_locals=True)

        if not hide:
            console.print(f"Deployed {self.__NAME__} to {path}")

'''
File access helper classes for optionally remote files.

'''

import contextlib
import io
import os
from pathlib import Path
from typing import List

from fabric.connection import Connection
from invoke.context import Context
from pydantic import BaseModel, root_validator

from .utils import console, filesystem


class BaseFile(BaseModel):
    __NAME__: str = None

    def __init_subclass__(cls):
        if cls.__NAME__ is None or not cls.__NAME__.strip():
            raise TypeError(
                "Template class must have a non-empty __NAME__ attribute defined"
            )

    @contextlib.contextmanager
    def open(self, c: Context, mode="r"):
        if mode == "r":
            yield io.StringIO(self.read_text(c))
        elif mode == "rb":
            yield io.BytesIO(self.read_bytes(c))
        else:
            raise RuntimeError("File is not writable")

    def read_text(self, c: Context):
        raise NotImplementedError

    def read_bytes(self: Context):
        raise NotImplementedError


class MultiPathFile(BaseFile):
    """ A file that can be in multiple optional paths."""

    paths: List[str] = []

    def read_text(self, c: Context):
        fs = filesystem(c)
        local_fs = filesystem(c, local=True)

        for path in self.paths:
            if fs.isfile(path):
                return fs.read_text(path)
            elif local_fs.isfile(path):
                return local_fs.read_text(path)

        raise FileNotFoundError(f"Could not find any of {self.paths} on remote or local")

    def read_bytes(self, c: Context):
        fs = filesystem(c)
        local_fs = filesystem(c, local=True)

        for path in self.paths:
            if fs.isfile(path):
                return fs.read_bytes(path)
            elif local_fs.isfile(path):
                return fs.read_bytes(path)
                
        raise FileNotFoundError(f"Could not find any of {self.paths} on remote or local")



class TemplateFile(BaseFile):
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
        super().__init_subclass__()

    def read_text(self):
        template = self.get_template()
        kwargs = self.dict()
        return template.format(**kwargs)

    def read_bytes(self):
        return self.read_text().encode()

    def deploy(self, c: Context, path, hide=False, warn=False):
        try:
            fs = filesystem(c)
            fs.makedirs(path, exist_ok=True)
            full_path = fs.sep.join([path, self.__NAME__])
            fs.write_text(full_path, self.read_text())
        except Exception as e:
            if not warn:
                raise e
            if not hide:
                console.print_exception(show_locals=True)

        if not hide:
            console.print(f"Deployed {self.__NAME__} to {path}")

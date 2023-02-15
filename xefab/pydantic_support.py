import inspect
import json
import re

import toml
import yaml
from fabric.tasks import Task
from invoke.context import Context
from makefun import create_function
from pydantic import BaseModel

from .utils import camel_to_snake, console


def read_file(file_path: str):
    fname, _, ext = file_path.rpartition(".")
    if ext == "json":
        with open(file_path) as f:
            data = json.load(f)
    elif ext in ["yaml", "yml"]:
        with open(file_path) as f:
            data = yaml.safe_load(f)
    elif ext == "toml":
        with open(file_path) as f:
            data = toml.load(f)
    else:
        raise ValueError(f"Unknown file extension {ext}")
    return data


def get_pydantic_signature(model, defaults={}):
    context_param = inspect.Parameter(
        "c",
        inspect.Parameter.POSITIONAL_ONLY,
        annotation=Context,
    )

    file_param = inspect.Parameter(
        "parse_file",
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        annotation=str,
        default=None,
    )

    params = [
        context_param,
        file_param,
    ]
    for name, field in model.__fields__.items():
        alias = field.alias
        for type_ in model.mro():
            if name in getattr(type_, "__annotations__", {}):
                annotation = type_.__annotations__[name]
                default = defaults.get(name, field.default)
                param = inspect.Parameter(
                    name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=default,
                    annotation=annotation,
                )
                params.append(param)

                if name == alias:
                    break

                alias_param = param = inspect.Parameter(
                    alias,
                    inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=annotation,
                )
                params.append(alias_param)
                break

    return inspect.Signature(params)


def get_pydantic_field_help(field, default=None):
    """
    Takes a model and a field name, and returns a string containing the field's title, description,
    and default value

    :param model: The model class
    :param field_name: The name of the field to get the help for
    :return: The help string for the field.
    """
    title = field.field_info.title
    description = field.field_info.description
    default = default or field.default
    help_str = ""
    if title:
        help_str = f"{title}: "
    if description:
        help_str += description
    if default:
        help_str += f" (default: {default})"
    return help_str


def task_from_model(model, *args, **kwargs):
    """
    Create a task from a pydantic model.
    The model must have a run method.
    The run method must accept a single parameter, the Context object.
    """
    model_class = model
    defaults = {}
    if not isinstance(model, type):
        model_class = model.__class__
        defaults = model.dict()
    class_name = model_class.__name__

    if not issubclass(model_class, BaseModel):
        raise TypeError(
            f"Cant create a task from type {model_class} must be a subclass of pydantic.BaseModel"
        )

    if not hasattr(model, "__call__"):
        raise TypeError(
            f"{model} must implement a __call__ method to be used as a task."
        )

    meth = getattr(model_class, "__call__")
    run_signature = inspect.signature(meth)

    if len(run_signature.parameters) != 2:
        raise TypeError(
            f"{class_name}.run must accept exactly two arguments: self and the Context object."
        )

    name = camel_to_snake(class_name)

    signature = get_pydantic_signature(model_class, defaults=defaults)

    def task_implementation(c, parse_file=None, **kwargs):
        if parse_file is not None:
            data = read_file(parse_file)
            cli_kwargs = {
                k: v for k, v in kwargs.items() if v != signature.parameters[k].default
            }
            merged = dict(data, **cli_kwargs)
            kwargs = dict(kwargs, **merged)
        model = model_class(**kwargs)
        return model(c)

    func = create_function(
        signature, task_implementation, func_name=name, doc=inspect.getdoc(meth)
    )

    task_class = kwargs.pop("klass", Task)
    default_help = {
        k: get_pydantic_field_help(field, defaults.get(k, None))
        for k, field in model.__fields__.items()
    }
    kwargs.setdefault("help", default_help)

    if not args:
        return task_class(func, **kwargs)

    # @task(pre, tasks, here)
    if "pre" in kwargs:
        raise TypeError("May not give *args and 'pre' kwarg simultaneously!")
    kwargs["pre"] = args
    return task_class(func, **kwargs)

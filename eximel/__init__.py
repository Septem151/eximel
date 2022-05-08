"""eximel top-level module"""
from importlib import metadata

__version__ = metadata.version("eximel")
_description = metadata.metadata("eximel")["summary"]

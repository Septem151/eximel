"""exceptions for eximel"""


class EximelError(Exception):
    """generic exception for eXiMeL parsing and interpreting errors"""


class EximelSyntaxError(EximelError):
    """exception for syntax error when parsing eXiMeL"""


class EximelRuntimeError(EximelError):
    """exception for runtime errors when interpreting eXiMeL"""

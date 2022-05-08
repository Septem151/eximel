"""eximel module entrypoint"""
import sys

from eximel.cli import main

sys.exit(main())  # type: ignore

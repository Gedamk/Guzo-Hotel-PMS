# -*- coding: utf-8 -*-
"""
Guzo Booking Bot package initializer.
"""

# Expose submodules
from . import modules
from . import reporting

__all__ = ["modules", "reporting"]
# -*- coding: utf-8 -*-
"""
Guzo Booking Bot package initializer.
Exposes reporting and modules cleanly.
"""

import importlib

# Explicitly load reporting.py as a submodule
reporting = importlib.import_module("guzo_backend.reporting")

# Import modules like email_sender
from .modules import email_sender

__all__ = [
    "reporting",
    "email_sender",
]
"""
Package initializer for guzo_backend.
"""
# Explicitly expose subpackages
from . import modules

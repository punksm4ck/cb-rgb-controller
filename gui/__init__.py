# gui/__init__.py

"""
Main GUI package for the RGB Controller application.
This file makes 'gui' a Python package and can optionally expose
key classes or functions from its submodules for easier access.
"""

# Expose the main GUI class for easier import if desired:
# from .controller import RGBControllerGUI

# Expose core components that might be used by an external launcher:
from .core.constants import APP_NAME, VERSION
from .core.exceptions import RGBControllerBaseException # Base exception for external handling

# __all__ can be used to define what 'from gui import *' would import
__all__ = [
    # "RGBControllerGUI", # Uncomment if you want to expose it directly via 'from gui import RGBControllerGUI'
    "APP_NAME",
    "VERSION",
    "RGBControllerBaseException"
]

# You can also perform package-level initializations here if necessary,
# though it's often kept minimal.
# print(f"GUI package ({APP_NAME} v{VERSION}) initialized.") # Example

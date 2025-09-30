# gui/effects/__init__.py

"""RGB lighting effects module"""

from .library import EffectLibrary, EffectState, AVAILABLE_EFFECTS
from .manager import EffectManager

__all__ = [
    'EffectLibrary', 
    'EffectManager',
    'EffectState',
    'AVAILABLE_EFFECTS'
]

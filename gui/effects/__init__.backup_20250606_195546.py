# gui/effects/__init__.py

"""RGB lighting effects module"""

from .library import EffectLibrary, EffectState, AVAILABLE_EFFECTS 
from .manager import EffectManager # Corrected to EffectManager

__all__ = [
    'EffectLibrary', 
    'EffectManager', # Corrected to EffectManager
    'EffectState' 
]


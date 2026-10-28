"""Schalter, Kaestchen und der Auswahlknopf der Sammlung.

Zusammen in einem Ordner, weil sie dieselbe Frage stellen - angekreuzt oder
nicht - und sich die Grundform _HaloTick teilen. Dass der Auswahlknopf nach
aussen ein QRadioButton ist und die uebrigen QCheckBox, aendert daran nichts.
"""

from .haloradiobutton import HaloRadioButton
from .halotoggles import FrameToggle, HaloCheckBox, LineToggle
from .heartcheckbox import HeartCheckBox
from .toggleswitch import AnimatedToggle

__all__ = [
    "AnimatedToggle", "FrameToggle", "HaloCheckBox", "HaloRadioButton",
    "HeartCheckBox", "LineToggle",
]

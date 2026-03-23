# ============================================================
# Group: 30
# Members: Christophe BOSHRA, Guillaume PORET
# File: objects.py
# ============================================================

class RadioactivityAgent:
    """
    Passive object present on every cell.
    Stores the zone and the radioactivity level.
    """
    def __init__(self, zone, level):
        self.zone = zone          # "z1", "z2", "z3"
        self.level = level        # float


class WasteAgent:
    """
    Passive waste object.
    waste_type in {"green", "yellow", "red"}
    """
    def __init__(self, waste_type):
        self.waste_type = waste_type


class WasteDisposalZoneAgent:
    """
    Passive disposal zone object.
    """
    def __init__(self):
        self.name = "waste_disposal_zone"
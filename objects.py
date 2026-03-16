import mesa
import random

class Radioactivity(mesa.Agent):
    """Agent inactif définissant la zone et le niveau de radioactivité d'une cellule."""
    def __init__(self, unique_id, model, zone):
        super().__init__(unique_id, model)
        self.zone = zone
        
        # Le niveau de radioactivité dépend de la zone
        if zone == "z1": # low radioactivity
            self.radioactivity = random.uniform(0, 0.33)
        elif zone == "z2": # medium radioactivity
            self.radioactivity = random.uniform(0.33, 0.66)
        elif zone == "z3": # high radioactivity
            self.radioactivity = random.uniform(0.66, 1.0)

class WasteDisposalZone(mesa.Agent):
    """Agent inactif représentant la zone où déposer les déchets rouges."""
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)

class Waste(mesa.Agent):
    """Agent inactif représentant un déchet."""
    def __init__(self, unique_id, model, color="green"):
        super().__init__(unique_id, model)
        self.color = color
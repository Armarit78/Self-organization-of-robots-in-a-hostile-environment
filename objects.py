import mesa
import random

class Radioactivity(mesa.Agent):
    """Agent inactif définissant la zone et le niveau de radioactivité d'une cellule."""
    def __init__(self, model, zone):
        super().__init__(model)
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
    def __init__(self, model):
        super().__init__(model)

class Waste(mesa.Agent):
    """Agent inactif représentant un déchet."""
    def __init__(self, model, color="green"):
        super().__init__(model)
        self.color = color

if __name__ == "__main__":
    print("--- Test indépendant de objects.py ---")
    
    # mesa.Agent a besoin d'un objet 'model' pour s'initialiser. 
    # On crée donc un faux modèle (Mock) très basique pour tester.
    class MockModel(mesa.Model):
        def __init__(self):
            super().__init__()
            
    dummy_model = MockModel()
    # Test de Radioactivity
    rad_z1 = Radioactivity(dummy_model, "z1")
    rad_z2   = Radioactivity(dummy_model, "z2")
    rad_z3 = Radioactivity(dummy_model, "z3")
    
    print(f"Radioactivité en Zone 1 (attendue: 0 à 0.33) : {rad_z1.radioactivity:.2f}")
    print(f"Radioactivité en Zone 2 (attendue: 0.33 à 0.66) : {rad_z2.radioactivity:.2f}")
    print(f"Radioactivité en Zone 3 (attendue: 0.66 à 1.0) : {rad_z3.radioactivity:.2f}")
    
    # Test de Waste
    waste = Waste(dummy_model, "red")
    waste2 = Waste(dummy_model, "green")
    waste3 = Waste(dummy_model, "yellow")
    print(f"Déchet créé, de couleur : {waste.color}")
    print(f"Déchet créé, de couleur : {waste2.color}")
    print(f"Déchet créé, de couleur : {waste3.color}")
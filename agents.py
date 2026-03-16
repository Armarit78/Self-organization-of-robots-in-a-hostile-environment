import mesa
import random
from objects import Waste, Radioactivity, WasteDisposalZone

# ==========================================
# FONCTIONS DE RAISONNEMENT (Hors des classes)
# ==========================================

def update(knowledge, percepts):
    """
    Met à jour la base de connaissances (knowledge) à partir des percepts.
    percepts est un dictionnaire renvoyé par model.do() : { (x,y): [objets_sur_la_case] }
    """
    knowledge["percepts"] = percepts
    knowledge["adjacent_cells"] = list(percepts.keys())
    
    # On peut analyser les percepts pour voir s'il y a des déchets autour
    # (À enrichir plus tard pour mémoriser la carte)
    return knowledge

def deliberate(knowledge):
    """
    Raisonnement de l'agent. Prend UNIQUEMENT 'knowledge' en entrée.
    Doit retourner une 'action' (ex: un dictionnaire).
    """
    # ÉTAPE 1 : Comportement aléatoire simple (comme suggéré par le sujet)
    possible_moves = knowledge.get("adjacent_cells", [])
    
    action = {"type": "idle"} # Par défaut, on ne fait rien
    
    # Déplacement aléatoire basique (le modèle vérifiera plus tard si le robot a le droit d'aller dans cette zone)
    if possible_moves:
        chosen_pos = random.choice(possible_moves)
        action = {"type": "move", "pos": chosen_pos}
        
    # TODO pour plus tard : Ajouter la logique pour "pick_up" (ramasser) 
    # si un déchet de la bonne couleur est dans les percepts.

    return action


# ==========================================
# CLASSES DES AGENTS
# ==========================================

class GenericRobot(mesa.Agent):
    """Classe parente pour mutualiser le comportement des robots."""
    def __init__(self, model):
        super().__init__(model)
        # Représentation des croyances et connaissances (imposé par le sujet)
        self.knowledge = {
            "inventory": [], # Pour stocker les déchets ramassés
            "percepts": {},
            "adjacent_cells": []
        }
        self.last_percepts = {}

    def step(self):
        """La boucle procédurale exacte demandée par le PDF."""
        
        # Au tout premier tour, l'agent n'a pas de percepts. On fait une action vide pour observer.
        if not self.last_percepts:
            self.last_percepts = self.model.do(self, {"type": "idle"})
        
        # 1. Update : l'agent met à jour ses connaissances
        update(self.knowledge, self.last_percepts)
        
        # 2. Deliberate : l'agent décide quoi faire (sans utiliser 'self')
        action = deliberate(self.knowledge)
        
        # 3. Do : l'agent transmet son action à l'environnement et reçoit les nouveaux percepts
        self.last_percepts = self.model.do(self, action)


class greenAgent(GenericRobot):
    def __init__(self, model):
        super().__init__(model)
        self.color = "green"
        self.allowed_zones = ["z1"] # Ne peut pas dépasser z1

class yellowAgent(GenericRobot):
    def __init__(self, model):
        super().__init__(model)
        self.color = "yellow"
        self.allowed_zones = ["z1", "z2"] # Peut aller en z1 et z2

class redAgent(GenericRobot):
    def __init__(self, model):
        super().__init__(model)
        self.color = "red"
        self.allowed_zones = ["z1", "z2", "z3"] # Peut aller partout

if __name__ == "__main__":
    print("--- Test indépendant de agents.py ---")
    
    # 1. Test des fonctions de raisonnement (logique pure)
    print("\n[1] Test de update()")
    knowledge = {"inventory": [], "percepts": {}, "adjacent_cells": []}
    percepts_mock = {(1, 1): ["Waste"], (1, 2): []}
    
    knowledge = update(knowledge, percepts_mock)
    print(f"Cellules adjacentes mises à jour : {knowledge['adjacent_cells']}")
    assert len(knowledge["adjacent_cells"]) == 2, "Erreur dans update()"
    
    print("\n[2] Test de deliberate()")
    action = deliberate(knowledge)
    print(f"Action choisie par l'agent : {action}")
    assert action["type"] in ["move", "idle"], "Erreur dans deliberate()"

    # 2. Test des classes avec un faux modèle adapté à Mesa 3
    print("\n[3] Test de création des agents")
    class MockModel(mesa.Model):
        def __init__(self):
            super().__init__()
            
    dummy_model = MockModel()
    
    robot_vert = greenAgent(dummy_model)
    print(f"Robot {robot_vert.color} créé, peut aller en : {robot_vert.allowed_zones}")
    
    robot_rouge = redAgent(dummy_model)
    print(f"Robot {robot_rouge.color} créé, peut aller en : {robot_rouge.allowed_zones}")
    print("\n--- agents.py fonctionne correctement ---")
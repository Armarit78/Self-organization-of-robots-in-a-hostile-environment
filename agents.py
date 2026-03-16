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
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
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
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.color = "green"
        self.allowed_zones = ["z1"] # Ne peut pas dépasser z1

class yellowAgent(GenericRobot):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.color = "yellow"
        self.allowed_zones = ["z1", "z2"] # Peut aller en z1 et z2

class redAgent(GenericRobot):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.color = "red"
        self.allowed_zones = ["z1", "z2", "z3"] # Peut aller partout
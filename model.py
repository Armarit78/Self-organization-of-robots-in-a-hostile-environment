import mesa
import random
from objects import Radioactivity, WasteDisposalZone, Waste
# from agents import GreenRobot, YellowRobot, RedRobot # A faire

# Fonctions pour le DataCollector
def compute_green_wastes(model):
    """Compte le nombre de déchets verts restants dans l'environnement."""
    wastes = [agent for agent in model.schedule.agents if isinstance(agent, Waste) and agent.color == "green"]
    return len(wastes)

def compute_yellow_wastes(model):
    wastes = [agent for agent in model.schedule.agents if isinstance(agent, Waste) and agent.color == "yellow"]
    return len(wastes)

def compute_red_wastes(model):
    wastes = [agent for agent in model.schedule.agents if isinstance(agent, Waste) and agent.color == "red"]
    return len(wastes)


class RobotMission(mesa.Model):
    def __init__(self, width=15, height=10, initial_wastes=10):
        super().__init__()
        self.grid = mesa.space.MultiGrid(width, height, torus=False)
        self.schedule = mesa.time.RandomActivation(self)
        self.current_id = 0

        # Configuration du DataCollector comme dans votre notebook
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Green Wastes": compute_green_wastes,
                "Yellow Wastes": compute_yellow_wastes,
                "Red Wastes": compute_red_wastes
            }
        )

        # Découpage des zones z1, z2, z3 d'ouest en est
        z1_max = width // 3
        z2_max = 2 * (width // 3)

        # 1. Placement des agents Radioactivité (sans comportement)
        for x in range(width):
            for y in range(height):
                if x < z1_max:
                    zone = "z1"
                elif x < z2_max:
                    zone = "z2"
                else:
                    zone = "z3"

                rad_agent = Radioactivity(self.next_id(), self, zone)
                self.grid.place_agent(rad_agent, (x, y))
                self.schedule.add(rad_agent)

        # 2. Placement de la zone de dépôt des déchets tout à l'Est
        disposal_y = random.randrange(height)
        disposal_zone = WasteDisposalZone(self.next_id(), self)
        self.grid.place_agent(disposal_zone, (width - 1, disposal_y))
        self.schedule.add(disposal_zone)

        # 3. Placement des déchets verts initiaux dans z1
        for _ in range(initial_wastes):
            x = random.randrange(z1_max)
            y = random.randrange(height)
            waste = Waste(self.next_id(), self, color="green")
            self.grid.place_agent(waste, (x, y))
            self.schedule.add(waste)
            
        # 4. Ajouter les robots

        self.running = True

    def do(self, agent, action):
        """
        Exécute l'action de l'agent si elle est faisable, puis renvoie les percepts[cite: 64, 65, 74].
        L'action peut être un dictionnaire ou une chaîne de caractères[cite: 45].
        """
        # Exemple d'implémentation basique de mouvement
        if isinstance(action, dict) and action.get("type") == "move":
            new_pos = action.get("pos")
            # Vérifier si la position est dans la grille
            if not self.grid.out_of_bounds(new_pos):
                self.grid.move_agent(agent, new_pos)
        
        # Exemple d'implémentation pour ramasser un déchet
        elif isinstance(action, dict) and action.get("type") == "pick_up":
            target_waste = action.get("waste")
            if target_waste in self.grid.get_cell_list_contents([agent.pos]):
                self.grid.remove_agent(target_waste)
                self.schedule.remove(target_waste)
                # Le robot devrait stocker le déchet dans son inventaire de son côté
        
        # Générer les percepts : infos sur les cases adjacentes
        percepts = {}
        neighborhood = self.grid.get_neighborhood(agent.pos, moore=True, include_center=True)
        for pos in neighborhood:
            # On stocke le contenu de chaque case (les objets/agents présents)
            percepts[pos] = self.grid.get_cell_list_contents([pos])
            
        return percepts

    def step(self):
        # Récolte des données à chaque tour, comme dans le notebook
        self.datacollector.collect(self)
        self.schedule.step()
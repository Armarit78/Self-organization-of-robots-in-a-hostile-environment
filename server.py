import mesa
from mesa.visualization import SolaraViz, make_plot_component, make_space_component
from model import RobotMission
from objects import Radioactivity, WasteDisposalZone, Waste
from agents import greenAgent, yellowAgent, redAgent

def agent_portrayal(agent):
    """
    Définit comment chaque agent doit être affiché sur la grille.
    - Radioactivity : Carrés transparents/légers
    - Zone de dépôt : Carré gris foncé
    - Déchets : Cercles de couleur (vert, jaune, rouge)
    - Robots : Triangles vifs
    """
    
    # --- OBJETS INACTIFS ---
    if isinstance(agent, Radioactivity):
        # On peut adapter l'opacité/couleur selon le niveau
        intensity = agent.radioactivity
        # z1: vert clair, z2: jaune clair, z3: rouge clair
        if agent.zone == "z1":
            color = "#ccffcc" # green light
        elif agent.zone == "z2":
            color = "#ffffcc" # yellow light
        else:
            color = "#ffcccc" # red light
        
        return {"color": color, "marker": "s", "size": 100} # s = square (carré)
        
    elif isinstance(agent, WasteDisposalZone):
        return {"color": "black", "marker": "s", "size": 150}
        
    elif isinstance(agent, Waste):
        return {"color": agent.color, "marker": "o", "size": 50} # o = circle (cercle)

    # --- ROBOTS ---
    elif isinstance(agent, greenAgent):
        return {"color": "green", "marker": "^", "size": 80} # ^ = triangle
    elif isinstance(agent, yellowAgent):
        return {"color": "yellow", "marker": "^", "size": 80}
    elif isinstance(agent, redAgent):
        return {"color": "red", "marker": "^", "size": 80}

    # Par sécurité (ne devrait jamais arriver)
    return {"color": "gray", "marker": "o", "size": 10}

# Paramètres interactifs de la simulation (Sliders)
model_params = {
    "width": 15,
    "height": 10,
    "initial_wastes": {
        "type": "SliderInt",
        "value": 15,
        "label": "Déchets verts initiaux",
        "min": 5,
        "max": 50,
        "step": 1,
    },
    "nb_green": {
        "type": "SliderInt",
        "value": 2,
        "label": "Robots Verts",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    "nb_yellow": {
        "type": "SliderInt",
        "value": 2,
        "label": "Robots Jaunes",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    "nb_red": {
        "type": "SliderInt",
        "value": 2,
        "label": "Robots Rouges",
        "min": 1,
        "max": 10,
        "step": 1,
    }
}

# Modèle initial
model_instance = RobotMission(width=15, height=10, initial_wastes=15, nb_green=2, nb_yellow=2, nb_red=2)

# Composants visuels de Solara
# 1. La grille de l'espace (Space Graph)
SpaceGraph = make_space_component(agent_portrayal)

# 2. Le graphique temporel des déchets restants
WastesPlot = make_plot_component(
    {"Green Wastes": "green", "Yellow Wastes": "yellow", "Red Wastes": "red"}
)

# Page contenant Dashboard SolaraViz (cette variable 'page' est lue automatiquement par Solara)
page = SolaraViz(
    model_instance,
    components=[SpaceGraph, WastesPlot],
    model_params=model_params,
    name="Robot Mission Visualization",
)

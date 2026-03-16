# ============================================================
# Group: GROUP_NUMBER
# Date: DATE
# Members: MEMBER_1, MEMBER_2, MEMBER_3
# File: model.py
# ============================================================

import random

from agents import greenAgent, yellowAgent, redAgent
from objects import RadioactivityAgent, WasteAgent


class RobotMission:
    def __init__(
        self,
        width=18,
        height=8,
        n_green_robots=3,
        n_yellow_robots=2,
        n_red_robots=2,
        n_initial_green_wastes=24,
        seed=42
    ):
        random.seed(seed)

        self.width = width
        self.height = height
        self.step_count = 0

        # zone boundaries
        self.z1_end = width // 3 - 1
        self.z2_end = (2 * width) // 3 - 1

        # grid data
        self.radioactivity_grid = {}
        self.waste_grid = {}       # {(x, y): [WasteAgent, ...]}
        self.robot_grid = {}       # {(x, y): [robot, ...]}

        self.agents = []

        # disposal zone: as far east as possible
        self.disposal_pos = (self.width - 1, random.randrange(self.height))

        self.stored_red_waste = 0

        self._create_environment()
        self._create_initial_wastes(n_initial_green_wastes)
        self._create_robots(n_green_robots, n_yellow_robots, n_red_robots)

    # ---------------------------------------------------------
    # Environment construction
    # ---------------------------------------------------------

    def _zone_of_x(self, x):
        if x <= self.z1_end:
            return "z1"
        if x <= self.z2_end:
            return "z2"
        return "z3"

    def _create_environment(self):
        for x in range(self.width):
            for y in range(self.height):
                zone = self._zone_of_x(x)

                if zone == "z1":
                    level = random.uniform(0.0, 0.33)
                elif zone == "z2":
                    level = random.uniform(0.33, 0.66)
                else:
                    level = random.uniform(0.66, 1.0)

                self.radioactivity_grid[(x, y)] = RadioactivityAgent(zone, level)

    def _create_initial_wastes(self, n_initial_green_wastes):
        z1_cells = [(x, y) for x in range(self.z1_end + 1) for y in range(self.height)]

        for _ in range(n_initial_green_wastes):
            pos = random.choice(z1_cells)
            self.waste_grid.setdefault(pos, []).append(WasteAgent("green"))

    def _place_robot(self, agent, pos):
        agent.pos = pos
        self.agents.append(agent)
        self.robot_grid.setdefault(pos, []).append(agent)

    def _create_robots(self, n_green, n_yellow, n_red):
        z1_cells = [(x, y) for x in range(self.z1_end + 1) for y in range(self.height)]
        z12_cells = [(x, y) for x in range(self.z2_end + 1) for y in range(self.height)]
        all_cells = [(x, y) for x in range(self.width) for y in range(self.height)]

        for i in range(n_green):
            a = greenAgent(f"G{i}", self)
            self._place_robot(a, random.choice(z1_cells))

        for i in range(n_yellow):
            a = yellowAgent(f"Y{i}", self)
            self._place_robot(a, random.choice(z12_cells))

        for i in range(n_red):
            a = redAgent(f"R{i}", self)
            self._place_robot(a, random.choice(all_cells))

    # ---------------------------------------------------------
    # Percepts
    # ---------------------------------------------------------

    def _neighbors_plus_current(self, pos):
        x, y = pos
        positions = [pos]

        candidates = [
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
        ]

        for cx, cy in candidates:
            if 0 <= cx < self.width and 0 <= cy < self.height:
                positions.append((cx, cy))

        return positions

    def get_percepts(self, agent):
        """
        Must return a dictionary describing adjacent tiles and their content.
        """
        percepts = {}
        positions = self._neighbors_plus_current(agent.pos)

        for pos in positions:
            radio = self.radioactivity_grid[pos]
            wastes = [w.waste_type for w in self.waste_grid.get(pos, [])]
            robots = [r.unique_id for r in self.robot_grid.get(pos, []) if r is not agent]

            percepts[pos] = {
                "zone": radio.zone,
                "radioactivity": radio.level,
                "wastes": wastes,
                "robots": robots,
                "disposal_zone": (pos == self.disposal_pos)
            }

        return percepts

    # ---------------------------------------------------------
    # Action execution
    # ---------------------------------------------------------

    def do(self, agent, action):
        """
        Check whether the action is feasible, then apply it.
        Return percepts as a dictionary.
        """
        action_type = action.get("type", "wait")

        if action_type == "move":
            self._do_move(agent, action)

        elif action_type == "pick":
            self._do_pick(agent)

        elif action_type == "transform":
            self._do_transform(agent)

        elif action_type == "drop":
            self._do_drop(agent)

        elif action_type == "wait":
            pass

        return self.get_percepts(agent)

    def _allowed_zones_for(self, agent):
        if isinstance(agent, greenAgent):
            return ["z1"]
        if isinstance(agent, yellowAgent):
            return ["z1", "z2"]
        if isinstance(agent, redAgent):
            return ["z1", "z2", "z3"]
        return []

    def _is_adjacent(self, from_pos, to_pos):
        fx, fy = from_pos
        tx, ty = to_pos
        return abs(fx - tx) + abs(fy - ty) == 1

    def _do_move(self, agent, action):
        if "to" not in action:
            return

        target = action["to"]
        tx, ty = target

        # check bounds
        if not (0 <= tx < self.width and 0 <= ty < self.height):
            return

        # check adjacency
        if not self._is_adjacent(agent.pos, target):
            return

        # check zone access
        target_zone = self.radioactivity_grid[target].zone
        if target_zone not in self._allowed_zones_for(agent):
            return

        # perform move
        old_pos = agent.pos
        if old_pos in self.robot_grid and agent in self.robot_grid[old_pos]:
            self.robot_grid[old_pos].remove(agent)
            if not self.robot_grid[old_pos]:
                del self.robot_grid[old_pos]

        agent.pos = target
        self.robot_grid.setdefault(target, []).append(agent)

    def _do_pick(self, agent):
        pos = agent.pos
        wastes = self.waste_grid.get(pos, [])

        if isinstance(agent, greenAgent):
            needed_type = "green"
        elif isinstance(agent, yellowAgent):
            needed_type = "yellow"
        elif isinstance(agent, redAgent):
            needed_type = "red"
        else:
            return

        for i, waste in enumerate(wastes):
            if waste.waste_type == needed_type:
                agent.inventory.append(needed_type)
                del wastes[i]
                if not wastes:
                    del self.waste_grid[pos]
                return

    def _do_transform(self, agent):
        if isinstance(agent, greenAgent):
            if agent.inventory.count("green") >= 2:
                removed = 0
                new_inventory = []
                for item in agent.inventory:
                    if item == "green" and removed < 2:
                        removed += 1
                    else:
                        new_inventory.append(item)
                new_inventory.append("yellow")
                agent.inventory = new_inventory

        elif isinstance(agent, yellowAgent):
            if agent.inventory.count("yellow") >= 2:
                removed = 0
                new_inventory = []
                for item in agent.inventory:
                    if item == "yellow" and removed < 2:
                        removed += 1
                    else:
                        new_inventory.append(item)
                new_inventory.append("red")
                agent.inventory = new_inventory

    def _do_drop(self, agent):
        pos = agent.pos

        # final storage by red robot on disposal zone
        if isinstance(agent, redAgent) and pos == self.disposal_pos and "red" in agent.inventory:
            agent.inventory.remove("red")
            self.stored_red_waste += 1
            return

        # regular drop on cell
        if not agent.inventory:
            return

        item = agent.inventory.pop(0)
        self.waste_grid.setdefault(pos, []).append(WasteAgent(item))

    # ---------------------------------------------------------
    # Simulation loop
    # ---------------------------------------------------------

    def step(self):
        random.shuffle(self.agents)
        for agent in self.agents:
            agent.step_agent()
        self.step_count += 1

    # ---------------------------------------------------------
    # Statistics / end condition
    # ---------------------------------------------------------

    def count_wastes_on_grid(self):
        counts = {"green": 0, "yellow": 0, "red": 0}
        for waste_list in self.waste_grid.values():
            for waste in waste_list:
                counts[waste.waste_type] += 1
        return counts

    def is_finished(self):
        counts = self.count_wastes_on_grid()
        hands_empty = all(len(agent.inventory) == 0 for agent in self.agents)

        return (
            counts["green"] == 0 and
            counts["yellow"] == 0 and
            counts["red"] == 0 and
            hands_empty
        )
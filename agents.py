# ============================================================
# Group: GROUP_NUMBER
# Date: DATE
# Members: MEMBER_1, MEMBER_2, MEMBER_3
# File: agents.py
# ============================================================

import random


class BaseRobotAgent:
    """
    Common parent class for all robot agents.
    Each concrete class must define its own robot_type.
    """

    def __init__(self, unique_id, model):
        self.unique_id = unique_id
        self.model = model
        self.pos = (0, 0)
        self.robot_type = "base"

        # Subject requirement:
        # self.knowledge represents beliefs/knowledge of the agent
        self.knowledge = {
            "self_id": unique_id,
            "robot_type": self.robot_type,
            "position": None,
            "inventory": [],
            "allowed_zones": [],
            "visible_cells": {},
            "known_wastes": {},       # {pos: [waste_types]}
            "known_disposal_zone": None,
            "history": []
        }

    def update_knowledge(self, percepts):
        """
        Update the internal knowledge from percepts.
        """
        self.knowledge["position"] = self.pos
        self.knowledge["inventory"] = self.inventory_copy()

        if self.robot_type == "green":
            self.knowledge["allowed_zones"] = ["z1"]
        elif self.robot_type == "yellow":
            self.knowledge["allowed_zones"] = ["z1", "z2"]
        elif self.robot_type == "red":
            self.knowledge["allowed_zones"] = ["z1", "z2", "z3"]

        self.knowledge["visible_cells"] = percepts

        for pos, cell_info in percepts.items():
            wastes = cell_info.get("wastes", [])
            if wastes:
                self.knowledge["known_wastes"][pos] = list(wastes)
            elif pos in self.knowledge["known_wastes"]:
                del self.knowledge["known_wastes"][pos]

            if cell_info.get("disposal_zone", False):
                self.knowledge["known_disposal_zone"] = pos

        self.knowledge["history"].append({
            "position": self.pos,
            "inventory": self.inventory_copy(),
            "percepts": percepts
        })

        if len(self.knowledge["history"]) > 50:
            self.knowledge["history"] = self.knowledge["history"][-50:]

    def inventory_copy(self):
        return list(getattr(self, "inventory", []))

    def step_agent(self):
        """
        Exact form requested by the subject:
        update(self.knowledge, percepts)
        action = deliberate(self.knowledge)
        percepts = self.model.do(self, action)
        """
        percepts = self.model.get_percepts(self)
        self.update_knowledge(percepts)
        action = self.deliberate(self.knowledge)
        percepts = self.model.do(self, action)
        self.update_knowledge(percepts)

    @staticmethod
    def deliberate(knowledge):
        """
        Must be overridden.
        Deliberate only uses its argument.
        """
        return {"type": "wait"}


class greenAgent(BaseRobotAgent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.robot_type = "green"
        self.inventory = []

    @staticmethod
    def deliberate(knowledge):
        """
        Green robot:
        - move in z1 only
        - pick 2 green wastes
        - transform into 1 yellow waste
        - if holding yellow waste, move east and drop it
        """
        position = knowledge["position"]
        x, y = position
        inventory = knowledge["inventory"]
        visible = knowledge["visible_cells"]
        known_wastes = knowledge["known_wastes"]

        current_cell = visible.get(position, {})
        current_wastes = current_cell.get("wastes", [])

        # If carrying yellow, move east if possible, otherwise drop
        if "yellow" in inventory:
            east_pos = (x + 1, y)
            if east_pos in visible and visible[east_pos]["zone"] == "z1":
                return {"type": "move", "to": east_pos}
            return {"type": "drop"}

        # If enough green wastes in inventory -> transform
        if inventory.count("green") >= 2:
            return {"type": "transform"}

        # If green waste on current cell -> pick
        if "green" in current_wastes:
            return {"type": "pick"}

        # Search nearest known green waste
        candidates = []
        for pos, wastes in known_wastes.items():
            if "green" in wastes:
                candidates.append(pos)

        if candidates:
            target = min(
                candidates,
                key=lambda p: abs(p[0] - x) + abs(p[1] - y)
            )
            tx, ty = target
            if tx > x:
                next_pos = (x + 1, y)
            elif tx < x:
                next_pos = (x - 1, y)
            elif ty > y:
                next_pos = (x, y + 1)
            elif ty < y:
                next_pos = (x, y - 1)
            else:
                next_pos = position

            if next_pos in visible and visible[next_pos]["zone"] == "z1":
                return {"type": "move", "to": next_pos}

        # Random legal move in z1
        neighbors = []
        for pos, info in visible.items():
            if pos != position and info["zone"] == "z1":
                neighbors.append(pos)

        if neighbors:
            return {"type": "move", "to": random.choice(neighbors)}

        return {"type": "wait"}


class yellowAgent(BaseRobotAgent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.robot_type = "yellow"
        self.inventory = []

    @staticmethod
    def deliberate(knowledge):
        """
        Yellow robot:
        - move in z1 and z2
        - pick 2 yellow wastes
        - transform into 1 red waste
        - if holding red waste, move east and drop it
        """
        position = knowledge["position"]
        x, y = position
        inventory = knowledge["inventory"]
        visible = knowledge["visible_cells"]
        known_wastes = knowledge["known_wastes"]

        current_cell = visible.get(position, {})
        current_wastes = current_cell.get("wastes", [])

        # If carrying red, move east if possible, otherwise drop
        if "red" in inventory:
            east_pos = (x + 1, y)
            if east_pos in visible and visible[east_pos]["zone"] in ["z1", "z2"]:
                return {"type": "move", "to": east_pos}
            return {"type": "drop"}

        # Transform 2 yellow -> 1 red
        if inventory.count("yellow") >= 2:
            return {"type": "transform"}

        # Pick if current cell contains yellow waste
        if "yellow" in current_wastes:
            return {"type": "pick"}

        # Search nearest known yellow waste
        candidates = []
        for pos, wastes in known_wastes.items():
            if "yellow" in wastes:
                candidates.append(pos)

        if candidates:
            target = min(
                candidates,
                key=lambda p: abs(p[0] - x) + abs(p[1] - y)
            )
            tx, ty = target
            if tx > x:
                next_pos = (x + 1, y)
            elif tx < x:
                next_pos = (x - 1, y)
            elif ty > y:
                next_pos = (x, y + 1)
            elif ty < y:
                next_pos = (x, y - 1)
            else:
                next_pos = position

            if next_pos in visible and visible[next_pos]["zone"] in ["z1", "z2"]:
                return {"type": "move", "to": next_pos}

        # Random legal move in z1/z2
        neighbors = []
        for pos, info in visible.items():
            if pos != position and info["zone"] in ["z1", "z2"]:
                neighbors.append(pos)

        if neighbors:
            return {"type": "move", "to": random.choice(neighbors)}

        return {"type": "wait"}


class redAgent(BaseRobotAgent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.robot_type = "red"
        self.inventory = []

    @staticmethod
    def deliberate(knowledge):
        """
        Red robot:
        - move in z1, z2, z3
        - pick 1 red waste
        - transport it to disposal zone
        - put it away there
        """
        position = knowledge["position"]
        x, y = position
        inventory = knowledge["inventory"]
        visible = knowledge["visible_cells"]
        known_wastes = knowledge["known_wastes"]
        disposal_pos = knowledge["known_disposal_zone"]

        current_cell = visible.get(position, {})
        current_wastes = current_cell.get("wastes", [])

        # If carrying red waste and on disposal zone -> drop
        if "red" in inventory and current_cell.get("disposal_zone", False):
            return {"type": "drop"}

        # If carrying red waste -> move toward disposal zone
        if "red" in inventory and disposal_pos is not None:
            dx, dy = disposal_pos
            if dx > x:
                return {"type": "move", "to": (x + 1, y)}
            if dx < x:
                return {"type": "move", "to": (x - 1, y)}
            if dy > y:
                return {"type": "move", "to": (x, y + 1)}
            if dy < y:
                return {"type": "move", "to": (x, y - 1)}
            return {"type": "wait"}

        # Pick if current cell contains red waste
        if "red" in current_wastes:
            return {"type": "pick"}

        # Search nearest known red waste
        candidates = []
        for pos, wastes in known_wastes.items():
            if "red" in wastes:
                candidates.append(pos)

        if candidates:
            target = min(
                candidates,
                key=lambda p: abs(p[0] - x) + abs(p[1] - y)
            )
            tx, ty = target
            if tx > x:
                return {"type": "move", "to": (x + 1, y)}
            if tx < x:
                return {"type": "move", "to": (x - 1, y)}
            if ty > y:
                return {"type": "move", "to": (x, y + 1)}
            if ty < y:
                return {"type": "move", "to": (x, y - 1)}

        # Random move anywhere visible
        neighbors = []
        for pos in visible:
            if pos != position:
                neighbors.append(pos)

        if neighbors:
            return {"type": "move", "to": random.choice(neighbors)}

        return {"type": "wait"}
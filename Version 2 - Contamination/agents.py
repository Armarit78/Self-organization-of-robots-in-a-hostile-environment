# ============================================================
# Group: 30
# Members: Christophe BOSHRA, Guillaume PORET
# File: agents.py
# ============================================================

import random

ROBOT_RESISTANCE_CONFIG = {
    "green": {
        "max_resistance": 18,
        "damage_per_item_per_step": 1,
    },
    "yellow": {
        "max_resistance": 20,
        "damage_per_item_per_step": 2,
    },
    "red": {
        "max_resistance": 25,
        "damage_per_item_per_step": 3,
    },
}

BASE_REGEN_PER_STEP = 1
KO_RECOVERY_STEPS = 5

def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class BaseRobotAgent:
    def __init__(self, unique_id, model):
        self.unique_id = unique_id
        self.model = model
        self.pos = (0, 0)
        self.robot_type = "base"
        self.inventory = []

        # V2 state
        self.max_resistance = 0
        self.resistance = 0
        self.damage_per_item_per_step = 0
        self.is_ko = False
        self.ko_remaining_steps = 0

        self.knowledge = {
            "self_id": unique_id,
            "robot_type": self.robot_type,
            "position": None,
            "inventory": [],
            "visible_cells": {},
            "known_wastes": {},
            "shared_targets": {},
            "claims": {},
            "robot_states": {},
            "buffer_pos": None,
            "known_disposal_zone": None,
            "communication_enabled": False,
            "z1_end": None,
            "z2_end": None,
            "height": None,
            "frontier_dir": None,

            # V2
            "base_pos": None,
            "resistance": 0,
            "max_resistance": 0,
            "is_ko": False,
            "ko_remaining_steps": 0,
            "ko_tasks": [],
        }

    def inventory_copy(self):
        return list(self.inventory)

    def _apply_robot_config(self):
        if self.robot_type not in ROBOT_RESISTANCE_CONFIG:
            return

        cfg = ROBOT_RESISTANCE_CONFIG[self.robot_type]
        self.max_resistance = cfg["max_resistance"]
        self.resistance = self.max_resistance
        self.damage_per_item_per_step = cfg["damage_per_item_per_step"]

    def update_knowledge(self, percepts):
        cells = percepts.get("cells", {})
        self.knowledge["position"] = self.pos
        self.knowledge["inventory"] = self.inventory_copy()
        self.knowledge["visible_cells"] = cells
        self.knowledge["shared_targets"] = percepts.get("shared_targets", {})
        self.knowledge["claims"] = percepts.get("claims", {})
        self.knowledge["robot_states"] = percepts.get("robot_states", {})
        self.knowledge["buffer_pos"] = percepts.get("buffer_pos")
        self.knowledge["communication_enabled"] = percepts.get("communication_enabled", False)
        self.knowledge["z1_end"] = percepts.get("z1_end")
        self.knowledge["z2_end"] = percepts.get("z2_end")
        self.knowledge["height"] = percepts.get("height")

        # disposal zone known globally
        self.knowledge["known_disposal_zone"] = percepts.get("disposal_pos")

        # V2
        self.knowledge["base_pos"] = percepts.get("base_pos")
        self.knowledge["resistance"] = percepts.get("resistance", self.resistance)
        self.knowledge["max_resistance"] = percepts.get("max_resistance", self.max_resistance)
        self.knowledge["is_ko"] = percepts.get("is_ko", self.is_ko)
        self.knowledge["ko_remaining_steps"] = percepts.get("ko_remaining_steps", self.ko_remaining_steps)
        self.knowledge["ko_tasks"] = percepts.get("ko_tasks", [])

        for pos, cell_info in cells.items():
            wastes = cell_info.get("wastes", [])
            if wastes:
                self.knowledge["known_wastes"][pos] = list(wastes)
            elif pos in self.knowledge["known_wastes"]:
                del self.knowledge["known_wastes"][pos]

    def step_agent(self):
        percepts = self.model.get_percepts(self)
        self.update_knowledge(percepts)
        action_bundle = self.deliberate(self.knowledge)
        percepts = self.model.do(self, action_bundle)
        self.update_knowledge(percepts)

    @staticmethod
    def deliberate(knowledge):
        return {"main": {"type": "wait"}, "reports": [], "claim": None}

    @staticmethod
    def _step_towards(position, target, visible, allowed_zones=None):
        x, y = position
        tx, ty = target

        candidates = []
        if tx > x:
            candidates.append((x + 1, y))
        elif tx < x:
            candidates.append((x - 1, y))

        if ty > y:
            candidates.append((x, y + 1))
        elif ty < y:
            candidates.append((x, y - 1))

        if not candidates:
            return None

        for p in candidates:
            if p in visible:
                if allowed_zones is None or visible[p]["zone"] in allowed_zones:
                    return p

        return None

    @staticmethod
    def _frontier_patrol_step(knowledge, frontier_x, allowed_zones):
        position = knowledge["position"]
        x, y = position
        visible = knowledge["visible_cells"]
        height = knowledge["height"]

        robot_num = int("".join(ch for ch in knowledge["self_id"] if ch.isdigit()) or 0)

        # 1) First go to the frontier column
        if x < frontier_x:
            next_pos = (x + 1, y)
            if next_pos in visible and visible[next_pos]["zone"] in allowed_zones:
                return next_pos

        if x > frontier_x:
            next_pos = (x - 1, y)
            if next_pos in visible and visible[next_pos]["zone"] in allowed_zones:
                return next_pos

        # 2) Once on the frontier, keep a persistent vertical direction
        direction = knowledge.get("frontier_dir")
        if direction not in (-1, 1):
            # even ids start downward, odd ids start upward
            direction = 1 if robot_num % 2 == 0 else -1
            knowledge["frontier_dir"] = direction

        # Bounce at borders
        if y == 0:
            direction = 1
            knowledge["frontier_dir"] = direction
        elif y == height - 1:
            direction = -1
            knowledge["frontier_dir"] = direction

        next_pos = (x, y + direction)
        if next_pos in visible and visible[next_pos]["zone"] in allowed_zones:
            return next_pos

        # If blocked vertically, reverse direction and try once
        direction = -direction
        knowledge["frontier_dir"] = direction

        next_pos = (x, y + direction)
        if next_pos in visible and visible[next_pos]["zone"] in allowed_zones:
            return next_pos

        # 3) Small lateral fallback, but stay near frontier
        lateral_candidates = [
            (frontier_x - 1, y),
            (frontier_x + 1, y),
        ]

        for p in lateral_candidates:
            if p in visible and visible[p]["zone"] in allowed_zones:
                return p

        return None

    @staticmethod
    def _green_rect_patrol_step(knowledge):
        position = knowledge["position"]
        x, y = position
        visible = knowledge["visible_cells"]
        z1_end = knowledge["z1_end"]
        height = knowledge["height"]

        robot_num = int("".join(ch for ch in knowledge["self_id"] if ch.isdigit()) or 0)

        # Divide z1 rows into 3 patrol bands
        # Example with height=8:
        # G0 -> rows 0..2
        # G1 -> rows 3..5
        # G2 -> rows 6..7
        band_size = max(1, height // 3)
        y_min = min(robot_num * band_size, height - 1)

        if robot_num == 2:
            y_max = height - 1
        else:
            y_max = min((robot_num + 1) * band_size - 1, height - 1)

        x_min = 0
        x_max = z1_end

        # Sense:
        # G0 clockwise
        # G1 counter-clockwise
        # G2 clockwise
        clockwise = (robot_num % 2 == 0)

        candidates = []

        if clockwise:
            # top edge -> move right
            if y == y_min and x < x_max:
                candidates.append((x + 1, y))
            # right edge -> move down
            elif x == x_max and y < y_max:
                candidates.append((x, y + 1))
            # bottom edge -> move left
            elif y == y_max and x > x_min:
                candidates.append((x - 1, y))
            # left edge -> move up
            elif x == x_min and y > y_min:
                candidates.append((x, y - 1))
        else:
            # left edge -> move down
            if x == x_min and y < y_max:
                candidates.append((x, y + 1))
            # bottom edge -> move right
            elif y == y_max and x < x_max:
                candidates.append((x + 1, y))
            # right edge -> move up
            elif x == x_max and y > y_min:
                candidates.append((x, y - 1))
            # top edge -> move left
            elif y == y_min and x > x_min:
                candidates.append((x - 1, y))

        # If not exactly on the patrol rectangle, move toward it
        if not candidates:
            target_x = min(max(x, x_min), x_max)
            target_y = min(max(y, y_min), y_max)

            if y < target_y:
                candidates.append((x, y + 1))
            elif y > target_y:
                candidates.append((x, y - 1))

            if x < target_x:
                candidates.append((x + 1, y))
            elif x > target_x:
                candidates.append((x - 1, y))

        # Final fallback inside z1
        candidates.extend([
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
        ])

        for p in candidates:
            if p in visible and visible[p]["zone"] == "z1":
                return p

        return None

    @staticmethod
    def _visible_reports(position, visible, waste_type, priority=1):
        reports = []
        for pos, cell in visible.items():
            if waste_type in cell.get("wastes", []):
                reports.append({
                    "waste_type": waste_type,
                    "position": pos,
                    "distance": manhattan(position, pos),
                    "priority": priority,
                })
        return reports

    @staticmethod
    def _best_unclaimed_target(self_id, position, visible, known_wastes, shared_targets, claims, wanted_type):
        candidates = []

        for pos, wastes in known_wastes.items():
            if wanted_type in wastes:
                candidates.append(pos)

        for pos in shared_targets.keys():
            if pos not in candidates:
                candidates.append(pos)

        filtered = []
        for pos in candidates:
            claim = claims.get(pos)
            if claim is None or claim["robot_id"] == self_id:
                filtered.append(pos)

        if not filtered:
            return None

        def target_score(p):
            shared_info = shared_targets.get(p, {})
            priority = shared_info.get("priority", 1)
            distance = manhattan(position, p)
            return distance - (2 * priority)

        return min(filtered, key=target_score)

    @staticmethod
    def _robot_numeric_id(robot_id):
        return int("".join(ch for ch in robot_id if ch.isdigit()) or 0)

    @staticmethod
    def _has_known_target_of_type(known_wastes, shared_targets, wanted_type):
        # Local knowledge: explicit waste lists
        for wastes in known_wastes.values():
            if wanted_type in wastes:
                return True

        # shared_targets is already filtered by type in model.get_percepts()
        # green robots receive shared_map["green"], yellow -> ["yellow"], red -> ["red"]
        return len(shared_targets) > 0

    @staticmethod
    def _best_ko_task(knowledge, wanted_type):
        position = knowledge["position"]
        self_id = knowledge["self_id"]
        tasks = knowledge.get("ko_tasks", [])

        candidates = []

        for task in tasks:
            if task.get("resolved"):
                continue
            if task.get("waste_type") != wanted_type:
                continue

            assigned_to = task.get("assigned_to")

            # keep my current task first
            if assigned_to == self_id:
                candidates.append((
                    0,  # strongest priority: keep current assignment
                    task.get("created_at", 0),
                    manhattan(position, task["position"]),
                    task,
                ))
                continue

            # free tasks only
            if assigned_to is None:
                candidates.append((
                    1,
                    task.get("created_at", 0),
                    manhattan(position, task["position"]),
                    task,
                ))

        if not candidates:
            return None

        # older first, then nearer
        candidates.sort(key=lambda x: (x[0], x[1], x[2]))
        return candidates[0][3]

    @staticmethod
    def _cooperative_drop_decision(knowledge, item_type, allowed_zones):
        """
        Safer cooperative exchange for isolated items.

        Principle:
        - communication must be enabled
        - robot must hold exactly one item of the given type
        - no known compatible target already exists
        - choose the closest same-type partner carrying exactly one item
        - lower numeric id = donor, higher numeric id = receiver
        - donor drops on the buffer, receiver picks from the buffer
        """
        if not knowledge["communication_enabled"]:
            return None

        position = knowledge["position"]
        inventory = knowledge["inventory"]
        visible = knowledge["visible_cells"]
        known_wastes = knowledge["known_wastes"]
        shared_targets = knowledge["shared_targets"]
        robot_states = knowledge["robot_states"]
        buffer_pos = knowledge["buffer_pos"]
        self_id = knowledge["self_id"]

        if buffer_pos is None:
            return None

        if inventory.count(item_type) != 1:
            return None

        # If a real compatible target already exists, do not force cooperation
        if BaseRobotAgent._has_known_target_of_type(known_wastes, shared_targets, item_type):
            return None

        # Find the nearest same-type partner carrying exactly one item
        partners = []
        for robot_id, state in robot_states.items():
            if robot_id == self_id:
                continue
            if state.get("inventory_count", 0) != 1:
                continue

            partner_pos = state.get("position")
            if partner_pos is None:
                continue

            partners.append(
                (
                    manhattan(position, partner_pos),
                    BaseRobotAgent._robot_numeric_id(robot_id),
                    robot_id,
                    partner_pos,
                )
            )

        if not partners:
            return None

        partners.sort()
        _, partner_num, partner_id, partner_pos = partners[0]

        self_num = BaseRobotAgent._robot_numeric_id(self_id)

        if self_num < partner_num:
            donor_id = self_id
            receiver_id = partner_id
        else:
            donor_id = partner_id
            receiver_id = self_id

        current_wastes = visible.get(position, {}).get("wastes", [])

        # DONOR
        if self_id == donor_id:
            if position == buffer_pos:
                if item_type in current_wastes:
                    return {
                        "main": {"type": "wait"},
                        "reports": [],
                        "status_reports": [],
                        "claim": None,
                    }

                return {
                    "main": {"type": "drop"},
                    "reports": [],
                    "status_reports": [],
                    "claim": None,
                }

            next_pos = BaseRobotAgent._step_towards(position, buffer_pos, visible, allowed_zones)
            if next_pos is not None:
                return {
                    "main": {"type": "move", "to": next_pos},
                    "reports": [],
                    "status_reports": [],
                    "claim": None,
                }

            return {
                "main": {"type": "wait"},
                "reports": [],
                "status_reports": [],
                "claim": None,
            }

        # RECEIVER
        if self_id == receiver_id:
            if position == buffer_pos:
                if item_type in current_wastes:
                    return {
                        "main": {"type": "pick"},
                        "reports": [],
                        "status_reports": [],
                        "claim": None,
                    }

                return {
                    "main": {"type": "wait"},
                    "reports": [],
                    "status_reports": [],
                    "claim": {"waste_type": item_type, "position": buffer_pos},
                }

            next_pos = BaseRobotAgent._step_towards(position, buffer_pos, visible, allowed_zones)
            if next_pos is not None:
                return {
                    "main": {"type": "move", "to": next_pos},
                    "reports": [],
                    "status_reports": [],
                    "claim": {"waste_type": item_type, "position": buffer_pos},
                }

            return {
                "main": {"type": "wait"},
                "reports": [],
                "status_reports": [],
                "claim": {"waste_type": item_type, "position": buffer_pos},
            }

        return None

    @staticmethod
    def _ko_action(knowledge, allowed_zones):
        position = knowledge["position"]
        visible = knowledge["visible_cells"]
        base_pos = knowledge["base_pos"]

        if base_pos is None:
            return {
                "main": {"type": "wait"},
                "reports": [],
                "status_reports": [],
                "claim": None,
            }

        if position != base_pos:
            next_pos = BaseRobotAgent._step_towards(position, base_pos, visible, allowed_zones)
            if next_pos is not None:
                return {
                    "main": {"type": "move", "to": next_pos},
                    "reports": [],
                    "status_reports": [],
                    "claim": None,
                }

        return {
            "main": {"type": "wait"},
            "reports": [],
            "status_reports": [],
            "claim": None,
        }


class greenAgent(BaseRobotAgent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.robot_type = "green"
        self.knowledge["robot_type"] = self.robot_type
        self._apply_robot_config()

    @staticmethod
    def deliberate(knowledge):
        if knowledge["is_ko"]:
            return BaseRobotAgent._ko_action(
                knowledge=knowledge,
                allowed_zones=["z1"],
            )

        position = knowledge["position"]
        x, y = position
        inventory = knowledge["inventory"]
        visible = knowledge["visible_cells"]
        known_wastes = knowledge["known_wastes"]
        shared_targets = knowledge["shared_targets"]
        z1_end = knowledge["z1_end"]

        reports = []
        status_reports = []

        if knowledge["communication_enabled"]:
            reports.extend(BaseRobotAgent._visible_reports(position, visible, "green", priority=1))
            reports.extend(BaseRobotAgent._visible_reports(position, visible, "yellow", priority=2))
            status_reports.append({
                "robot_type": "green",
                "robot_id": knowledge["self_id"],
                "position": position,
                "inventory_count": len(inventory),
            })

        current_cell = visible.get(position, {})
        current_wastes = current_cell.get("wastes", [])

        if "yellow" in inventory:
            target_drop_x = z1_end
            if x < target_drop_x:
                next_pos = (x + 1, y)
                if next_pos in visible and visible[next_pos]["zone"] == "z1":
                    return {
                        "main": {"type": "move", "to": next_pos},
                        "reports": reports,
                        "status_reports": status_reports,
                        "claim": None,
                    }
            return {
                "main": {"type": "drop"},
                "reports": reports,
                "status_reports": status_reports,
                "claim": None,
            }

        if inventory.count("green") >= 2:
            return {
                "main": {"type": "transform"},
                "reports": reports,
                "status_reports": status_reports,
                "claim": None,
            }

        if "green" in current_wastes:
            return {
                "main": {"type": "pick"},
                "reports": reports,
                "status_reports": status_reports,
                "claim": None,
            }

        coop_action = BaseRobotAgent._cooperative_drop_decision(
            knowledge=knowledge,
            item_type="green",
            allowed_zones=["z1"],
        )
        if coop_action is not None:
            coop_action["reports"] = reports
            coop_action["status_reports"] = status_reports
            return coop_action

        target = BaseRobotAgent._best_unclaimed_target(
            self_id=knowledge["self_id"],
            position=position,
            visible=visible,
            known_wastes=known_wastes,
            shared_targets=shared_targets,
            claims=knowledge["claims"],
            wanted_type="green",
        )

        if target is not None:
            next_pos = BaseRobotAgent._step_towards(position, target, visible, ["z1"])
            if next_pos is not None:
                return {
                    "main": {"type": "move", "to": next_pos},
                    "reports": reports,
                    "status_reports": status_reports,
                    "claim": {"waste_type": "green", "position": target},
                }

        next_pos = BaseRobotAgent._green_rect_patrol_step(knowledge)

        if next_pos is not None:
            return {
                "main": {"type": "move", "to": next_pos},
                "reports": reports,
                "status_reports": status_reports,
                "claim": None,
            }

        return {
            "main": {"type": "wait"},
            "reports": reports,
            "status_reports": status_reports,
            "claim": None,
        }


class yellowAgent(BaseRobotAgent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.robot_type = "yellow"
        self.knowledge["robot_type"] = self.robot_type
        self._apply_robot_config()

    @staticmethod
    def deliberate(knowledge):
        if knowledge["is_ko"]:
            return BaseRobotAgent._ko_action(
                knowledge=knowledge,
                allowed_zones=["z1", "z2"],
            )

        position = knowledge["position"]
        x, y = position
        inventory = knowledge["inventory"]
        visible = knowledge["visible_cells"]
        known_wastes = knowledge["known_wastes"]
        shared_targets = knowledge["shared_targets"]
        claims = knowledge["claims"]
        z2_end = knowledge["z2_end"]
        self_id = knowledge["self_id"]

        reports = []
        status_reports = []

        if knowledge["communication_enabled"]:
            reports.extend(BaseRobotAgent._visible_reports(position, visible, "yellow", priority=1))
            reports.extend(BaseRobotAgent._visible_reports(position, visible, "red", priority=3))
            status_reports.append({
                "robot_type": "yellow",
                "robot_id": knowledge["self_id"],
                "position": position,
                "inventory_count": len(inventory),
            })

        current_cell = visible.get(position, {})
        current_wastes = current_cell.get("wastes", [])

        if "red" in inventory:
            target_drop_x = z2_end
            if x < target_drop_x:
                next_pos = (x + 1, y)
                if next_pos in visible and visible[next_pos]["zone"] in ["z1", "z2"]:
                    return {
                        "main": {"type": "move", "to": next_pos},
                        "reports": reports,
                        "status_reports": status_reports,
                        "claim": None,
                    }
            return {
                "main": {"type": "drop"},
                "reports": reports,
                "status_reports": status_reports,
                "claim": None,
            }

        if inventory.count("yellow") >= 2:
            return {
                "main": {"type": "transform"},
                "reports": reports,
                "status_reports": status_reports,
                "claim": None,
            }

        if "yellow" in current_wastes:
            return {
                "main": {"type": "pick"},
                "reports": reports,
                "status_reports": status_reports,
                "claim": None,
            }

        coop_action = BaseRobotAgent._cooperative_drop_decision(
            knowledge=knowledge,
            item_type="yellow",
            allowed_zones=["z1", "z2"],
        )
        if coop_action is not None:
            coop_action["reports"] = reports
            coop_action["status_reports"] = status_reports
            return coop_action

        ko_task = BaseRobotAgent._best_ko_task(
            knowledge=knowledge,
            wanted_type="yellow",
        )

        if ko_task is not None:
            emergency_target = ko_task["position"]

            # already there -> let normal pick logic happen on next checks
            if position != emergency_target:
                next_pos = BaseRobotAgent._step_towards(
                    position,
                    emergency_target,
                    visible,
                    ["z1", "z2"]
                )
                if next_pos is not None:
                    return {
                        "main": {"type": "move", "to": next_pos},
                        "reports": reports,
                        "status_reports": status_reports,
                        "claim": {"waste_type": "yellow", "position": emergency_target},
                        "ko_claim": {"waste_type": "yellow", "task_id": ko_task["task_id"]},
                    }

        target = BaseRobotAgent._best_unclaimed_target(
            self_id=self_id,
            position=position,
            visible=visible,
            known_wastes=known_wastes,
            shared_targets=shared_targets,
            claims=claims,
            wanted_type="yellow",
        )

        if target is not None:
            next_pos = BaseRobotAgent._step_towards(position, target, visible, ["z1", "z2"])
            if next_pos is not None:
                return {
                    "main": {"type": "move", "to": next_pos},
                    "reports": reports,
                    "status_reports": status_reports,
                    "claim": {"waste_type": "yellow", "position": target},
                }

        next_pos = BaseRobotAgent._frontier_patrol_step(
            knowledge=knowledge,
            frontier_x=knowledge["z1_end"],
            allowed_zones=["z1", "z2"],
        )

        if next_pos is not None:
            return {
                "main": {"type": "move", "to": next_pos},
                "reports": reports,
                "status_reports": status_reports,
                "claim": None,
            }

        return {
            "main": {"type": "wait"},
            "reports": reports,
            "status_reports": status_reports,
            "claim": None,
        }


class redAgent(BaseRobotAgent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.robot_type = "red"
        self.knowledge["robot_type"] = self.robot_type
        self._apply_robot_config()

    @staticmethod
    def deliberate(knowledge):
        if knowledge["is_ko"]:
            return BaseRobotAgent._ko_action(
                knowledge=knowledge,
                allowed_zones=["z1", "z2", "z3"],
            )

        position = knowledge["position"]
        inventory = knowledge["inventory"]
        visible = knowledge["visible_cells"]
        known_wastes = knowledge["known_wastes"]
        shared_targets = knowledge["shared_targets"]
        claims = knowledge["claims"]
        disposal_pos = knowledge["known_disposal_zone"]
        self_id = knowledge["self_id"]

        reports = []
        status_reports = []

        if knowledge["communication_enabled"]:
            reports.extend(BaseRobotAgent._visible_reports(position, visible, "red", priority=3))
            status_reports.append({
                "robot_type": "red",
                "robot_id": self_id,
                "position": position,
                "inventory_count": len(inventory),
            })

        current_cell = visible.get(position, {})
        current_wastes = current_cell.get("wastes", [])

        if "red" in inventory and current_cell.get("disposal_zone", False):
            return {
                "main": {"type": "drop"},
                "reports": reports,
                "status_reports": status_reports,
                "claim": None,
            }

        if "red" in inventory and disposal_pos is not None:
            if position == disposal_pos:
                return {
                    "main": {"type": "drop"},
                    "reports": reports,
                    "status_reports": status_reports,
                    "claim": None,
                }

            next_pos = BaseRobotAgent._step_towards(position, disposal_pos, visible, ["z1", "z2", "z3"])
            if next_pos is not None:
                return {
                    "main": {"type": "move", "to": next_pos},
                    "reports": reports,
                    "status_reports": status_reports,
                    "claim": None,
                }

            return {
                "main": {"type": "wait"},
                "reports": reports,
                "status_reports": status_reports,
                "claim": None,
            }

        if "red" in current_wastes:
            return {
                "main": {"type": "pick"},
                "reports": reports,
                "status_reports": status_reports,
                "claim": None,
            }

        ko_task = BaseRobotAgent._best_ko_task(
            knowledge=knowledge,
            wanted_type="red",
        )

        if ko_task is not None:
            emergency_target = ko_task["position"]

            if position != emergency_target:
                next_pos = BaseRobotAgent._step_towards(
                    position,
                    emergency_target,
                    visible,
                    ["z1", "z2", "z3"]
                )
                if next_pos is not None:
                    return {
                        "main": {"type": "move", "to": next_pos},
                        "reports": reports,
                        "status_reports": status_reports,
                        "claim": {"waste_type": "red", "position": emergency_target},
                        "ko_claim": {"waste_type": "red", "task_id": ko_task["task_id"]},
                    }

        target = BaseRobotAgent._best_unclaimed_target(
            self_id=self_id,
            position=position,
            visible=visible,
            known_wastes=known_wastes,
            shared_targets=shared_targets,
            claims=claims,
            wanted_type="red",
        )

        if target is not None:
            next_pos = BaseRobotAgent._step_towards(position, target, visible, ["z1", "z2", "z3"])
            if next_pos is not None:
                return {
                    "main": {"type": "move", "to": next_pos},
                    "reports": reports,
                    "status_reports": status_reports,
                    "claim": {"waste_type": "red", "position": target},
                }

        next_pos = BaseRobotAgent._frontier_patrol_step(
            knowledge=knowledge,
            frontier_x=knowledge["z2_end"],
            allowed_zones=["z1", "z2", "z3"],
        )

        if next_pos is not None:
            return {
                "main": {"type": "move", "to": next_pos},
                "reports": reports,
                "status_reports": status_reports,
                "claim": None,
            }

        return {
            "main": {"type": "wait"},
            "reports": reports,
            "status_reports": status_reports,
            "claim": None,
        }
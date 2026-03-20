# ============================================================
# Group: GROUP_NUMBER
# Date: DATE
# Members: MEMBER_1, MEMBER_2, MEMBER_3
# File: model.py
# ============================================================

import random

from agents import greenAgent, yellowAgent, redAgent
from objects import RadioactivityAgent, WasteAgent, WasteDisposalZoneAgent


class RobotMission:
    def __init__(
            self,
            width=18,
            height=8,
            n_green_robots=3,
            n_yellow_robots=2,
            n_red_robots=2,
            n_initial_green_wastes=None,
            seed=32,
            communication_enabled=True,
            max_steps=2000,
    ):
        random.seed(seed)

        self.width = width
        self.height = height
        self.step_count = 0
        self.model_id = random.randint(100000, 999999)
        self.communication_enabled = communication_enabled
        self.max_steps = max_steps

        if n_initial_green_wastes is None:
            z1_width = width // 3
            z1_capacity = z1_width * height
            n_initial_green_wastes = random.randint(12, max(12, z1_capacity // 2))

        self.z1_end = width // 3 - 1
        self.z2_end = (2 * width) // 3 - 1

        self.radioactivity_grid = {}
        self.waste_grid = {}
        self.robot_grid = {}

        self.agents = []

        self.disposal_pos = (self.width - 1, random.randrange(self.height))
        self.disposal_agent = WasteDisposalZoneAgent()

        self.stored_red_waste = 0
        self.message_count = 0
        self.finished_at = None

        # important for your current setup:
        # 4 green -> 1 stored red
        self.initial_green_wastes = n_initial_green_wastes
        self.expected_stored_red = self.initial_green_wastes // 4

        ## shared map by waste type
        self.shared_map = {
            "green": {},    # pos -> {"last_seen": step, "reporter": "...", "distance": ..., "priority": ...}
            "yellow": {},
            "red": {},
        }

        self.claims = {
            "green": {},  # pos -> {"robot_id": "...", "step": ...}
            "yellow": {},
            "red": {},
        }

        self.shared_robot_state = {
            "green": {},  # robot_id -> {"position": (...), "inventory_count": int, "last_seen": step}
            "yellow": {},
            "red": {},
        }

        self.report_ttl = 20
        self.claim_ttl = 8

        self.history = {
            "steps": [],
            "green": [],
            "yellow": [],
            "red": [],
            "stored_red": [],
            "messages": [],
        }

        # Deadlock / no-progress tracking
        self.last_progress_step = 0
        self.deadlock_patience = 25 if communication_enabled else 0

        self._create_environment()
        self._create_initial_wastes(n_initial_green_wastes)
        self._create_robots(n_green_robots, n_yellow_robots, n_red_robots)
        self.record_history()

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
    # Shared map / claims
    # ---------------------------------------------------------

    def _cleanup_shared_state(self):
        for waste_type in ["green", "yellow", "red"]:
            # remove outdated reports
            for pos in list(self.shared_map[waste_type].keys()):
                report = self.shared_map[waste_type][pos]
                if self.step_count - report["last_seen"] > self.report_ttl:
                    del self.shared_map[waste_type][pos]

            # remove outdated claims
            for pos in list(self.claims[waste_type].keys()):
                claim = self.claims[waste_type][pos]
                if self.step_count - claim["step"] > self.claim_ttl:
                    del self.claims[waste_type][pos]

            # remove outdated robot status
            for robot_id in list(self.shared_robot_state[waste_type].keys()):
                state = self.shared_robot_state[waste_type][robot_id]
                if self.step_count - state["last_seen"] > self.report_ttl:
                    del self.shared_robot_state[waste_type][robot_id]

            # remove stale entries if waste no longer exists there
            for pos in list(self.shared_map[waste_type].keys()):
                actual = [w.waste_type for w in self.waste_grid.get(pos, [])]
                if waste_type not in actual:
                    del self.shared_map[waste_type][pos]
                    if pos in self.claims[waste_type]:
                        del self.claims[waste_type][pos]

    def _publish_report(self, reporter_id, waste_type, position, report=None):
        if not self.communication_enabled:
            return
        if waste_type not in ["green", "yellow", "red"]:
            return

        if report is None:
            report = {}

        position = tuple(position)
        existing = self.shared_map[waste_type].get(position)

        new_report = {
            "waste_type": waste_type,
            "last_seen": self.step_count,
            "reporter": reporter_id,
            "distance": report.get("distance", 0),
            "priority": report.get("priority", 1),
        }

        if existing != new_report:
            self.message_count += 1

        self.shared_map[waste_type][position] = new_report

    def _claim_target(self, robot_id, waste_type, position):
        if waste_type not in ["green", "yellow", "red"]:
            return
        position = tuple(position)
        self.claims[waste_type][position] = {
            "robot_id": robot_id,
            "step": self.step_count,
        }

    def _release_claim_if_any(self, robot_id, waste_type):
        if waste_type not in ["green", "yellow", "red"]:
            return
        for pos in list(self.claims[waste_type].keys()):
            if self.claims[waste_type][pos]["robot_id"] == robot_id:
                del self.claims[waste_type][pos]

    def _buffer_pos_for(self, robot_type):
        if robot_type == "green":
            return (self.z1_end, self.height // 2)
        if robot_type == "yellow":
            return (self.z2_end, self.height // 2)
        return None

    def _publish_robot_status(self, robot_id, robot_type, position, inventory_count):
        if not self.communication_enabled:
            return
        if robot_type not in ["green", "yellow", "red"]:
            return

        new_state = {
            "position": tuple(position),
            "inventory_count": inventory_count,
            "last_seen": self.step_count,
        }

        existing = self.shared_robot_state[robot_type].get(robot_id)
        if existing != new_state:
            self.message_count += 1

        self.shared_robot_state[robot_type][robot_id] = new_state

    def _can_any_robot_transform(self, robot_type):
        if robot_type == "green":
            return any(agent.inventory.count("green") >= 2 for agent in self.agents if isinstance(agent, greenAgent))
        if robot_type == "yellow":
            return any(agent.inventory.count("yellow") >= 2 for agent in self.agents if isinstance(agent, yellowAgent))
        return False

    def _mark_progress(self):
        self.last_progress_step = self.step_count

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
        cells = {}
        positions = self._neighbors_plus_current(agent.pos)

        for pos in positions:
            radio = self.radioactivity_grid[pos]
            wastes = [w.waste_type for w in self.waste_grid.get(pos, [])]
            robots = [r.unique_id for r in self.robot_grid.get(pos, []) if r is not agent]

            cells[pos] = {
                "zone": radio.zone,
                "radioactivity": radio.level,
                "wastes": wastes,
                "robots": robots,
                "disposal_zone": (pos == self.disposal_pos),
            }

        if agent.robot_type == "green":
            shared = dict(self.shared_map["green"])
            claims = dict(self.claims["green"])
            robot_states = dict(self.shared_robot_state["green"])
        elif agent.robot_type == "yellow":
            shared = dict(self.shared_map["yellow"])
            claims = dict(self.claims["yellow"])
            robot_states = dict(self.shared_robot_state["yellow"])
        elif agent.robot_type == "red":
            shared = dict(self.shared_map["red"])
            claims = dict(self.claims["red"])
            robot_states = dict(self.shared_robot_state["red"])
        else:
            shared = {}
            claims = {}
            robot_states = {}

        return {
            "cells": cells,
            "shared_targets": shared,
            "claims": claims,
            "robot_states": robot_states,
            "buffer_pos": self._buffer_pos_for(agent.robot_type),
            "communication_enabled": self.communication_enabled,
            "z1_end": self.z1_end,
            "z2_end": self.z2_end,
            "disposal_pos": self.disposal_pos,
            "height": self.height,
        }

    # ---------------------------------------------------------
    # Action execution
    # ---------------------------------------------------------

    def do(self, agent, action_bundle):
        """
        action_bundle format:
        {
            "main": {...},
            "reports": [{"waste_type": "...", "position": (...)}, ...],
            "claim": {"waste_type": "...", "position": (...)} | None
        }
        """
        if action_bundle is None:
            action_bundle = {}

        reports = action_bundle.get("reports", [])
        status_reports = action_bundle.get("status_reports", [])
        claim = action_bundle.get("claim")
        main_action = action_bundle.get("main", {"type": "wait"})

        # communication does not consume the turn anymore
        for report in reports:
            self._publish_report(
                reporter_id=agent.unique_id,
                waste_type=report.get("waste_type"),
                position=report.get("position"),
                report=report,
            )

        for status in status_reports:
            self._publish_robot_status(
                robot_id=status.get("robot_id", agent.unique_id),
                robot_type=status.get("robot_type", agent.robot_type),
                position=status.get("position", agent.pos),
                inventory_count=status.get("inventory_count", 0),
            )

        if claim is not None:
            self._claim_target(
                robot_id=agent.unique_id,
                waste_type=claim.get("waste_type"),
                position=claim.get("position"),
            )

        action_type = main_action.get("type", "wait")

        if action_type == "move":
            self._do_move(agent, main_action)
        elif action_type == "pick":
            self._do_pick(agent)
        elif action_type == "transform":
            self._do_transform(agent)
        elif action_type == "drop":
            self._do_drop(agent)
        elif action_type == "wait":
            pass

        self._cleanup_shared_state()
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

        if not (0 <= tx < self.width and 0 <= ty < self.height):
            return

        if not self._is_adjacent(agent.pos, target):
            return

        target_zone = self.radioactivity_grid[target].zone
        if target_zone not in self._allowed_zones_for(agent):
            return

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

                if needed_type in ["green", "yellow", "red"]:
                    if pos in self.shared_map[needed_type]:
                        del self.shared_map[needed_type][pos]
                    if pos in self.claims[needed_type]:
                        del self.claims[needed_type][pos]

                self._mark_progress()
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
                self._release_claim_if_any(agent.unique_id, "green")
                self._mark_progress()

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
                self._release_claim_if_any(agent.unique_id, "yellow")
                self._mark_progress()

    def _do_drop(self, agent):
        pos = agent.pos

        # Red robot storing final red waste
        if isinstance(agent, redAgent) and pos == self.disposal_pos and "red" in agent.inventory:
            agent.inventory.remove("red")
            self.stored_red_waste += 1
            print(
                f"[STORE] model_id={self.model_id} step={self.step_count} "
                f"robot={agent.unique_id} stored_red_waste={self.stored_red_waste}"
            )
            self._release_claim_if_any(agent.unique_id, "red")
            self._mark_progress()
            return

        if not agent.inventory:
            return

        # Drop the item that matches the robot's current mission logic
        item = None

        if isinstance(agent, greenAgent):
            if "yellow" in agent.inventory:
                item = "yellow"
            elif "green" in agent.inventory:
                item = "green"

        elif isinstance(agent, yellowAgent):
            if "red" in agent.inventory:
                item = "red"
            elif "yellow" in agent.inventory:
                item = "yellow"

        elif isinstance(agent, redAgent):
            if "red" in agent.inventory:
                item = "red"

        if item is None:
            return

        agent.inventory.remove(item)
        self.waste_grid.setdefault(pos, []).append(WasteAgent(item))
        self._mark_progress()

        # publish useful intermediate waste automatically only when relevant
        if item == "green" and self.communication_enabled:
            if self.radioactivity_grid[pos].zone == "z1":
                self._publish_report(
                    agent.unique_id,
                    "green",
                    pos,
                    report={"distance": 0, "priority": 1},
                )

        elif item == "yellow" and self.communication_enabled:
            if self.radioactivity_grid[pos].zone in ["z1", "z2"]:
                self._publish_report(
                    agent.unique_id,
                    "yellow",
                    pos,
                    report={"distance": 0, "priority": 2},
                )

        elif item == "red" and self.communication_enabled:
            if pos != self.disposal_pos:
                self._publish_report(
                    agent.unique_id,
                    "red",
                    pos,
                    report={"distance": 0, "priority": 3},
                )

    # ---------------------------------------------------------
    # Simulation loop
    # ---------------------------------------------------------

    def step(self):
        if self.finished_at is not None:
            return

        if self.step_count >= self.max_steps:
            self.finished_at = self.step_count
            return

        random.shuffle(self.agents)
        for agent in self.agents:
            agent.step_agent()

        self.step_count += 1
        self._cleanup_shared_state()
        self.record_history()

        if self.is_finished() and self.finished_at is None:
            self.finished_at = self.step_count
        elif self.step_count >= self.max_steps and self.finished_at is None:
            self.finished_at = self.step_count

    # ---------------------------------------------------------
    # Statistics / end condition
    # ---------------------------------------------------------

    def count_wastes_on_grid(self):
        counts = {"green": 0, "yellow": 0, "red": 0}
        for waste_list in self.waste_grid.values():
            for waste in waste_list:
                counts[waste.waste_type] += 1
        return counts

    def record_history(self):
        counts = self.count_wastes_on_grid()

        if self.history["stored_red"]:
            previous_value = self.history["stored_red"][-1]
            if self.stored_red_waste < previous_value:
                print(
                    f"[BUG] model_id={self.model_id} stored_red_waste decreased: "
                    f"{previous_value} -> {self.stored_red_waste}"
                )

        self.history["steps"].append(self.step_count)
        self.history["green"].append(counts["green"])
        self.history["yellow"].append(counts["yellow"])
        self.history["red"].append(counts["red"])
        self.history["stored_red"].append(self.stored_red_waste)
        self.history["messages"].append(self.message_count)

    def is_finished(self):
        if self.step_count >= self.max_steps:
            return True

        # Success criterion
        if self.stored_red_waste >= self.expected_stored_red:
            return True

        counts = self.count_wastes_on_grid()

        green_in_hands = sum(agent.inventory.count("green") for agent in self.agents)
        yellow_in_hands = sum(agent.inventory.count("yellow") for agent in self.agents)
        red_in_hands = sum(agent.inventory.count("red") for agent in self.agents)

        total_green = counts["green"] + green_in_hands
        total_yellow = counts["yellow"] + yellow_in_hands
        total_red = counts["red"] + red_in_hands

        # If red already exists somewhere, phase can still progress
        if total_red > 0:
            return False

        # If a yellow robot can still transform, phase can still progress
        if self._can_any_robot_transform("yellow"):
            return False

        # If yellow wastes still exist on the grid, phase can still progress
        if counts["yellow"] > 0:
            return False

        # If a green robot can still transform, phase can still progress
        if self._can_any_robot_transform("green"):
            return False

        # If green wastes still exist on the grid, phase can still progress
        if counts["green"] > 0:
            return False

        # Phase 2: allow a short recovery window for cooperation,
        # but stop if there has been no real material progress
        if self.communication_enabled:
            steps_without_progress = self.step_count - self.last_progress_step
            if steps_without_progress <= self.deadlock_patience:
                return False

        # No more reachable progress
        return True
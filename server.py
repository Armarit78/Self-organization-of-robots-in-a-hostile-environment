# ============================================================
# Group: GROUP_NUMBER
# Date: DATE
# Members: MEMBER_1, MEMBER_2, MEMBER_3
# File: server.py
# ============================================================

from agents import greenAgent, yellowAgent, redAgent


def _cell_symbol(model, pos):
    if pos == model.disposal_pos:
        return "D"

    robots = model.robot_grid.get(pos, [])
    wastes = model.waste_grid.get(pos, [])

    if robots:
        if any(isinstance(r, greenAgent) for r in robots):
            return "G"
        if any(isinstance(r, yellowAgent) for r in robots):
            return "Y"
        if any(isinstance(r, redAgent) for r in robots):
            return "R"

    if wastes:
        types = [w.waste_type for w in wastes]
        if "red" in types:
            return "r"
        if "yellow" in types:
            return "y"
        if "green" in types:
            return "g"

    zone = model.radioactivity_grid[pos].zone
    if zone == "z1":
        return "."
    if zone == "z2":
        return ":"
    return ";"


def render(model):
    lines = []
    lines.append("=" * (model.width + 35))
    lines.append(f"STEP: {model.step_count}")
    lines.append(f"DISPOSAL ZONE: {model.disposal_pos}")
    lines.append(f"STORED RED WASTE: {model.stored_red_waste}")
    lines.append("Legend: G/Y/R robots | g/y/r wastes | D disposal | .=z1 :=z2 ;=z3")
    lines.append("-" * (model.width + 35))

    for y in range(model.height):
        row = []
        for x in range(model.width):
            row.append(_cell_symbol(model, (x, y)))
        lines.append("".join(row))

    lines.append("-" * (model.width + 35))

    for agent in model.agents:
        lines.append(f"{agent.unique_id} at {agent.pos} inventory={agent.inventory}")

    counts = model.count_wastes_on_grid()
    lines.append("-" * (model.width + 35))
    lines.append(
        f"Wastes on grid -> green: {counts['green']} | yellow: {counts['yellow']} | red: {counts['red']}"
    )

    return "\n".join(lines)
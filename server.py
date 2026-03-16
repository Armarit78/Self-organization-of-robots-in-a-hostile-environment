# ============================================================
# Group: GROUP_NUMBER
# Date: DATE
# Members: MEMBER_1, MEMBER_2, MEMBER_3
# File: server.py
# ============================================================

import asyncio
import matplotlib.pyplot as plt
import solara
from solara.lab import use_task

from agents import greenAgent, yellowAgent, redAgent
from model import RobotMission


def create_model():
    return RobotMission(
        width=18,
        height=8,
        n_green_robots=3,
        n_yellow_robots=2,
        n_red_robots=2,
        n_initial_green_wastes=24,
        seed=42,
    )


def cell_symbol(model, pos):
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
        return ""   # empty clean cell in z1
    if zone == "z2":
        return ""
    return ""


def cell_color(model, pos):
    if pos == model.disposal_pos:
        return "#212121"

    robots = model.robot_grid.get(pos, [])
    wastes = model.waste_grid.get(pos, [])

    if robots:
        if any(isinstance(r, greenAgent) for r in robots):
            return "#43a047"
        if any(isinstance(r, yellowAgent) for r in robots):
            return "#fbc02d"
        if any(isinstance(r, redAgent) for r in robots):
            return "#e53935"

    if wastes:
        types = [w.waste_type for w in wastes]
        if "red" in types:
            return "#ef9a9a"
        if "yellow" in types:
            return "#fff59d"
        if "green" in types:
            return "#a5d6a7"

    zone = model.radioactivity_grid[pos].zone
    if zone == "z1":
        return "#e8f5e9"
    if zone == "z2":
        return "#fffde7"
    return "#ffebee"


def cell_border(model, pos):
    if pos == model.disposal_pos:
        return "2px solid #000000"

    zone = model.radioactivity_grid[pos].zone
    if zone == "z1":
        return "1px solid #81c784"
    if zone == "z2":
        return "1px solid #ffd54f"
    return "1px solid #ef9a9a"


def count_all_wastes(model):
    counts = model.count_wastes_on_grid()
    return counts["green"], counts["yellow"], counts["red"]


@solara.component
def StatCard(title, value):
    with solara.Card(style={"min-width": "180px", "text-align": "center"}):
        solara.Markdown(f"**{title}**")
        solara.Markdown(f"## {value}")


@solara.component
def GridView(model, version):
    _ = version

    with solara.Card("Environment"):
        with solara.Column(gap="4px"):
            for y in range(model.height):
                with solara.Row(gap="4px"):
                    for x in range(model.width):
                        pos = (x, y)
                        symbol = cell_symbol(model, pos)
                        color = cell_color(model, pos)
                        border = cell_border(model, pos)

                        solara.Markdown(
                            f"""
<div style="
width:42px;
height:42px;
display:flex;
align-items:center;
justify-content:center;
border-radius:10px;
border:{border};
background:{color};
font-weight:700;
font-size:18px;
color:#111;
box-shadow:0 1px 3px rgba(0,0,0,0.12);
user-select:none;
">
{symbol}
</div>
"""
                        )


@solara.component
def Legend():
    with solara.Card("Legend"):
        with solara.Column(gap="2px"):
            solara.Text("Green robot = G")
            solara.Text("Yellow robot = Y")
            solara.Text("Red robot = R")
            solara.Text("Green waste = g")
            solara.Text("Yellow waste = y")
            solara.Text("Red waste = r")
            solara.Text("Disposal zone = D")
            solara.Text("Background colors show z1 / z2 / z3")


@solara.component
def AgentTable(model, version):
    _ = version

    with solara.Card("Agents status"):
        for agent in model.agents:
            solara.Text(f"{agent.unique_id} | position={agent.pos} | inventory={agent.inventory}")


@solara.component
def SimulationInfo(model, version):
    _ = version
    counts = model.count_wastes_on_grid()

    with solara.Card("Simulation info"):
        with solara.Row(gap="16px"):
            StatCard("Step", model.step_count)
            StatCard("Stored red waste", model.stored_red_waste)
            StatCard("Green wastes", counts["green"])
            StatCard("Yellow wastes", counts["yellow"])
            StatCard("Red wastes", counts["red"])
            StatCard("Disposal zone", model.disposal_pos)


@solara.component
def WasteChart(model, version):
    _ = version

    fig = plt.figure(figsize=(8, 4))
    ax = fig.add_subplot(111)

    ax.plot(model.history["steps"], model.history["green"], label="Green waste")
    ax.plot(model.history["steps"], model.history["yellow"], label="Yellow waste")
    ax.plot(model.history["steps"], model.history["red"], label="Red waste")
    ax.plot(model.history["steps"], model.history["stored_red"], label="Stored red waste")

    ax.set_title("Waste evolution over time")
    ax.set_xlabel("Step")
    ax.set_ylabel("Count")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    with solara.Card("Chart"):
        solara.FigureMatplotlib(fig)


@solara.component
def Page():
    model, set_model = solara.use_state(create_model())
    version, set_version = solara.use_state(0)
    auto_run, set_auto_run = solara.use_state(False)
    speed, set_speed = solara.use_state(0.20)

    def step_once():
        if not model.is_finished():
            model.step()
            set_version(version + 1)

    def reset_model():
        set_model(create_model())
        set_version(version + 1)
        set_auto_run(False)

    def toggle_auto():
        set_auto_run(not auto_run)

    async def auto_loop():
        while auto_run and not model.is_finished():
            await asyncio.sleep(speed)
            model.step()
            set_version(lambda v: v + 1)

    use_task(auto_loop, dependencies=[auto_run, speed, model])

    solara.Title("Self-organization of robots in a hostile environment")

    with solara.Column(gap="20px"):
        solara.Markdown("## Robot Mission - Phase 1")

        with solara.Row(gap="12px"):
            solara.Button("STEP", on_click=step_once)
            solara.Button("RESET", on_click=reset_model)
            solara.Button(
                "STOP AUTO" if auto_run else "START AUTO",
                on_click=toggle_auto,
            )

        with solara.Card("Controls"):
            solara.SliderFloat(
                label="Simulation speed (seconds per step)",
                value=speed,
                min=0.05,
                max=1.0,
                step=0.05,
                on_value=set_speed,
            )

        SimulationInfo(model, version)

        with solara.Columns([2, 1]):
            GridView(model, version)
            with solara.Column():
                Legend()
                AgentTable(model, version)

        WasteChart(model, version)
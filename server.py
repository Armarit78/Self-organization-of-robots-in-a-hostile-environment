# ============================================================
# Group: 30
# Members: Christophe BOSHRA, Guillaume PORET
# File: server.py
# ============================================================

import asyncio
import random
import matplotlib.pyplot as plt
import solara
from solara.lab import use_task

from agents import greenAgent, yellowAgent, redAgent
from model import RobotMission


DEFAULT_PARAMS = dict(
    width=18,
    height=8,
    n_green_robots=3,
    n_yellow_robots=2,
    n_red_robots=2,
)


def create_phase1_model(seed, n_initial_green_wastes=None):
    return RobotMission(
        **DEFAULT_PARAMS,
        seed=seed,
        n_initial_green_wastes=n_initial_green_wastes,
        communication_enabled=False,
    )


def create_phase2_model(seed, n_initial_green_wastes=None):
    return RobotMission(
        **DEFAULT_PARAMS,
        seed=seed,
        n_initial_green_wastes=n_initial_green_wastes,
        communication_enabled=True,
    )


def cell_symbol(model, pos):
    if pos == model.disposal_pos:
        return "D"

    if hasattr(model, "base_positions"):
        if pos == model.base_positions.get("green"):
            return "Bv"
        if pos == model.base_positions.get("yellow"):
            return "By"
        if pos == model.base_positions.get("red"):
            return "Br"

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

    return ""


def cell_color(model, pos):
    if pos == model.disposal_pos:
        return "#212121"

    if hasattr(model, "base_positions"):
        if pos == model.base_positions.get("green"):
            return "#1b5e20"
        if pos == model.base_positions.get("yellow"):
            return "#f57f17"
        if pos == model.base_positions.get("red"):
            return "#b71c1c"

    robots = model.robot_grid.get(pos, [])
    wastes = model.waste_grid.get(pos, [])

    if robots:
        for r in robots:
            if isinstance(r, greenAgent):
                return "#1b5e20" if not getattr(r, "is_ko", False) else "#000000"
            if isinstance(r, yellowAgent):
                return "#fbc02d" if not getattr(r, "is_ko", False) else "#000000"
            if isinstance(r, redAgent):
                return "#c62828" if not getattr(r, "is_ko", False) else "#000000"

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


@solara.component
def StatCard(title, value):
    with solara.Card(style={"min-width": "150px", "text-align": "center"}):
        solara.Markdown(f"**{title}**")
        solara.Markdown(f"## {value}")


@solara.component
def GridView(model, version, title):
    _ = version
    with solara.Card(title):
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
width:32px;
height:32px;
display:flex;
align-items:center;
justify-content:center;
border-radius:8px;
border:{border};
background:{color};
font-weight:700;
font-size:16px;
color:#111;
user-select:none;
">
{symbol}
</div>
"""
                        )


@solara.component
def ModelInfo(model, version, title):
    _ = version
    counts = model.count_wastes_on_grid()

    with solara.Card(title):
        solara.Text(f"Step: {model.step_count}")
        solara.Text(f"Model ID: {model.model_id}")
        solara.Text(f"Green wastes: {counts['green']}")
        solara.Text(f"Yellow wastes: {counts['yellow']}")
        solara.Text(f"Red wastes: {counts['red']}")
        solara.Text(f"Stored red waste: {model.stored_red_waste}")
        solara.Text(f"Messages sent: {model.message_count}")
        solara.Text(f"Communication: {'ON' if model.communication_enabled else 'OFF'}")
        solara.Text(f"Finished at: {model.finished_at if model.finished_at is not None else '-'}")
        solara.Text(f"Expected stored red: {model.expected_stored_red}")

@solara.component
def RobotInventories(model, version, title):
    _ = version

    def robot_sort_key(agent):
        digits = "".join(ch for ch in str(agent.unique_id) if ch.isdigit())
        return (agent.robot_type, int(digits or 0), str(agent.unique_id))

    sorted_agents = sorted(model.agents, key=robot_sort_key)

    with solara.Card(title):
        if not sorted_agents:
            solara.Text("No robots")
            return

        for agent in sorted_agents:
            inventory_text = ", ".join(agent.inventory) if agent.inventory else "empty"
            ko_text = f" | KO({agent.ko_remaining_steps})" if getattr(agent, "is_ko", False) else ""
            solara.Text(
                f"{agent.unique_id} | type={agent.robot_type} | pos={agent.pos} "
                f"| res={getattr(agent, 'resistance', 0)}/{getattr(agent, 'max_resistance', 0)}"
                f"{ko_text} | inventory=[{inventory_text}]"
            )


@solara.component
def Legend():
    with solara.Card("Legend"):
        solara.Text("Green robot = G")
        solara.Text("Yellow robot = Y")
        solara.Text("Red robot = R")
        solara.Text("Green waste = g")
        solara.Text("Yellow waste = y")
        solara.Text("Red waste = r")
        solara.Text("Disposal zone = D")
        solara.Text("Green base = Bv")
        solara.Text("Yellow base = By")
        solara.Text("Red base = Br")
        solara.Text("KO robot = ✖")


@solara.component
def VersusSummary(model1, model2, version):
    _ = version

    step1 = model1.finished_at if model1.finished_at is not None else model1.step_count
    step2 = model2.finished_at if model2.finished_at is not None else model2.step_count

    if step1 > 0:
        improvement = ((step1 - step2) / step1) * 100
    else:
        improvement = 0.0

    with solara.Card("Phase 1 vs Phase 2"):
        solara.Text(f"Phase 1 steps: {step1}")
        solara.Text(f"Phase 2 steps: {step2}")
        solara.Text(f"Phase 1 messages: {model1.message_count}")
        solara.Text(f"Phase 2 messages: {model2.message_count}")
        solara.Text(f"Improvement (based on current steps): {improvement:.2f}%")

        if model1.is_finished() and model2.is_finished():
            solara.Markdown(
                f"**Final improvement:** {improvement:.2f}% fewer steps for Phase 2"
            )


@solara.component
def VersusChart(model1, model2, version):
    _ = version

    fig = plt.figure(figsize=(10, 5))
    ax = fig.add_subplot(111)

    ax.plot(model1.history["steps"], model1.history["green"], label="P1 green")
    ax.plot(model1.history["steps"], model1.history["yellow"], label="P1 yellow")
    ax.plot(model1.history["steps"], model1.history["red"], label="P1 red on grid")
    ax.plot(model1.history["steps"], model1.history["stored_red"], label="P1 stored red (cumulative)")

    ax.plot(model2.history["steps"], model2.history["green"], label="P2 green", linestyle="--")
    ax.plot(model2.history["steps"], model2.history["yellow"], label="P2 yellow", linestyle="--")
    ax.plot(model2.history["steps"], model2.history["red"], label="P2 red on grid", linestyle="--")
    ax.plot(model2.history["steps"], model2.history["stored_red"], label="P2 stored red (cumulative)", linestyle="--")

    ax.set_title("Phase 1 vs Phase 2")
    ax.set_xlabel("Step")
    ax.set_ylabel("Count")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    with solara.Card("Versus chart"):
        solara.FigureMatplotlib(fig)


@solara.component
def Page():
    z1_width = DEFAULT_PARAMS["width"] // 3
    z1_capacity = z1_width * DEFAULT_PARAMS["height"]

    initial_seed, set_initial_seed = solara.use_state(random.randint(0, 100000))
    initial_wastes, set_initial_wastes = solara.use_state(
        random.randint(12, max(12, z1_capacity // 2))
    )

    model1, set_model1 = solara.use_state(create_phase1_model(seed=initial_seed, n_initial_green_wastes=initial_wastes))
    model2, set_model2 = solara.use_state(create_phase2_model(seed=initial_seed, n_initial_green_wastes=initial_wastes))

    version, set_version = solara.use_state(0)
    auto_run, set_auto_run = solara.use_state(False)
    speed, set_speed = solara.use_state(0.20)

    def step_both():
        if not model1.is_finished():
            model1.step()
        if not model2.is_finished():
            model2.step()
        set_version(version + 1)

    def reset_both():
        new_seed = random.randint(0, 100000)
        new_initial_wastes = random.randint(12, max(12, z1_capacity // 2))

        set_initial_seed(new_seed)
        set_initial_wastes(new_initial_wastes)
        set_model1(create_phase1_model(seed=new_seed, n_initial_green_wastes=new_initial_wastes))
        set_model2(create_phase2_model(seed=new_seed, n_initial_green_wastes=new_initial_wastes))
        set_version(version + 1)
        set_auto_run(False)

    def toggle_auto():
        set_auto_run(not auto_run)

    async def auto_loop():
        while auto_run and (not model1.is_finished() or not model2.is_finished()):
            await asyncio.sleep(speed)
            if not model1.is_finished():
                model1.step()
            if not model2.is_finished():
                model2.step()
            set_version(lambda v: v + 1)

    use_task(auto_loop, dependencies=[auto_run, speed, model1, model2])

    solara.Title("Robot Mission - Phase 1 vs Phase 2")

    with solara.Column(gap="20px"):
        solara.Markdown("## Same environment, different strategy")
        solara.Markdown("Phase 1 = no communication | Phase 2 = communication enabled")

        with solara.Row(gap="12px"):
            solara.Button("STEP BOTH", on_click=step_both)
            solara.Button("RESET BOTH", on_click=reset_both)
            solara.Button("STOP AUTO" if auto_run else "START AUTO", on_click=toggle_auto)

        with solara.Card("Controls"):
            solara.SliderFloat(
                label="Simulation speed (seconds per step)",
                value=speed,
                min=0.05,
                max=1.0,
                step=0.05,
                on_value=set_speed,
            )

        VersusSummary(model1, model2, version)

        with solara.Columns([1, 1]):
            with solara.Column():
                ModelInfo(model1, version, "Phase 1")
                GridView(model1, version, "Phase 1 grid")
                RobotInventories(model1, version, "Phase 1 robot inventories")
            with solara.Column():
                ModelInfo(model2, version, "Phase 2")
                GridView(model2, version, "Phase 2 grid")
                RobotInventories(model2, version, "Phase 2 robot inventories")

        Legend()
        VersusChart(model1, model2, version)
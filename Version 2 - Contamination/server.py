# ============================================================
# Group: 30
# Members: Christophe BOSHRA, Guillaume PORET
# File: server.py
# ============================================================

import asyncio
import random
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
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

ZONE_BG = {"z1": "#e8f5e9", "z2": "#fffde7", "z3": "#ffebee"}
ZONE_BORDER = {"z1": "1px solid #81c784", "z2": "1px solid #ffd54f", "z3": "1px solid #ef9a9a"}

ROBOT_COLORS = {"green": "#1b5e20", "yellow": "#fbc02d", "red": "#c62828"}
WASTE_COLORS = {"green": "#a5d6a7", "yellow": "#fff59d", "red": "#ef9a9a"}
BASE_COLORS = {"green": "#1b5e20", "yellow": "#f57f17", "red": "#b71c1c"}
HP_BAR_COLORS = {"green": "#4caf50", "yellow": "#ffeb3b", "red": "#f44336"}


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


# ---------------------------------------------------------
# Cell rendering
# ---------------------------------------------------------

def cell_symbol(model, pos):
    if pos == model.disposal_pos:
        return "D"

    if hasattr(model, "base_positions"):
        for rtype, label in [("green", "Bv"), ("yellow", "By"), ("red", "Br")]:
            if pos == model.base_positions.get(rtype):
                return label

    robots = model.robot_grid.get(pos, [])
    if robots:
        r = robots[0]
        if getattr(r, "is_ko", False):
            return "KO"
        if isinstance(r, greenAgent):
            return "G"
        if isinstance(r, yellowAgent):
            return "Y"
        if isinstance(r, redAgent):
            return "R"

    wastes = model.waste_grid.get(pos, [])
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
        for rtype in ["green", "yellow", "red"]:
            if pos == model.base_positions.get(rtype):
                return BASE_COLORS[rtype]

    robots = model.robot_grid.get(pos, [])
    if robots:
        r = robots[0]
        if getattr(r, "is_ko", False):
            return "#000000"
        return ROBOT_COLORS.get(r.robot_type, "#888")

    wastes = model.waste_grid.get(pos, [])
    if wastes:
        types = [w.waste_type for w in wastes]
        for t in ["red", "yellow", "green"]:
            if t in types:
                return WASTE_COLORS[t]

    zone = model.radioactivity_grid[pos].zone
    return ZONE_BG.get(zone, "#fff")


def cell_border(model, pos):
    if pos == model.disposal_pos:
        return "2px solid #000000"
    zone = model.radioactivity_grid[pos].zone
    return ZONE_BORDER.get(zone, "1px solid #ccc")


def cell_text_color(model, pos):
    robots = model.robot_grid.get(pos, [])
    if robots and getattr(robots[0], "is_ko", False):
        return "#f44336"
    if pos == model.disposal_pos:
        return "#fff"
    if hasattr(model, "base_positions"):
        for rtype in ["green", "yellow", "red"]:
            if pos == model.base_positions.get(rtype):
                return "#fff"
    return "#111"


# ---------------------------------------------------------
# Components
# ---------------------------------------------------------

@solara.component
def GridView(model, version, title):
    _ = version
    with solara.Card(title):
        with solara.Column(gap="2px"):
            for y in range(model.height):
                with solara.Row(gap="2px"):
                    for x in range(model.width):
                        pos = (x, y)
                        symbol = cell_symbol(model, pos)
                        color = cell_color(model, pos)
                        border = cell_border(model, pos)
                        txt_color = cell_text_color(model, pos)
                        font_size = "11px" if len(symbol) > 1 else "14px"

                        solara.Markdown(
                            f'<div style="'
                            f"width:30px;height:30px;"
                            f"display:flex;align-items:center;justify-content:center;"
                            f"border-radius:6px;border:{border};"
                            f"background:{color};color:{txt_color};"
                            f"font-weight:700;font-size:{font_size};"
                            f'user-select:none;">'
                            f"{symbol}</div>"
                        )


@solara.component
def StatsTable(model, version, title):
    """Compact stats table replacing the old ModelInfo text list."""
    _ = version
    counts = model.count_wastes_on_grid()
    status = "Finished" if model.finished_at is not None else "Running"
    step_display = model.finished_at if model.finished_at is not None else model.step_count

    rows = [
        ("Step", f"{step_display}"),
        ("Status", status),
        ("Déchets verts", f"{counts['green']}"),
        ("Déchets jaunes", f"{counts['yellow']}"),
        ("Déchets rouges", f"{counts['red']}"),
        ("Stockés", f"{model.stored_red_waste} / {model.expected_stored_red}"),
        ("Messages", f"{model.message_count}"),
    ]

    html_rows = "".join(
        f'<tr><td style="padding:3px 10px;font-weight:600;white-space:nowrap">{k}</td>'
        f'<td style="padding:3px 10px;text-align:right">{v}</td></tr>'
        for k, v in rows
    )

    with solara.Card(title):
        solara.Markdown(
            f'<table style="width:100%;border-collapse:collapse;font-size:14px">'
            f"<tbody>{html_rows}</tbody></table>"
        )


@solara.component
def RobotStatusTable(model, version, title):
    """HP bars and status for each robot in a compact table."""
    _ = version

    def sort_key(a):
        digits = "".join(ch for ch in str(a.unique_id) if ch.isdigit())
        return ({"green": 0, "yellow": 1, "red": 2}.get(a.robot_type, 9), int(digits or 0))

    sorted_agents = sorted(model.agents, key=sort_key)

    rows_html = ""
    for agent in sorted_agents:
        hp = getattr(agent, "resistance", 0)
        hp_max = getattr(agent, "max_resistance", 1)
        is_ko = getattr(agent, "is_ko", False)
        ko_rem = getattr(agent, "ko_remaining_steps", 0)
        inv = agent.inventory

        pct = max(0, min(100, int(100 * hp / hp_max))) if hp_max > 0 else 0
        bar_color = HP_BAR_COLORS.get(agent.robot_type, "#888")

        if is_ko:
            bar_color = "#f44336"
            status_badge = f'<span style="color:#f44336;font-weight:700">KO ({ko_rem})</span>'
        else:
            status_badge = f'<span style="color:#4caf50;font-weight:700">OK</span>'

        hp_bar = (
            f'<div style="width:80px;height:14px;background:#e0e0e0;border-radius:7px;overflow:hidden;display:inline-block;vertical-align:middle">'
            f'<div style="width:{pct}%;height:100%;background:{bar_color};border-radius:7px"></div>'
            f"</div>"
            f'<span style="font-size:11px;margin-left:4px">{hp}/{hp_max}</span>'
        )

        inv_text = ", ".join(inv) if inv else "-"

        rows_html += (
            f"<tr>"
            f'<td style="padding:2px 6px;font-weight:700">{agent.unique_id}</td>'
            f'<td style="padding:2px 6px">{agent.pos}</td>'
            f'<td style="padding:2px 6px">{hp_bar}</td>'
            f'<td style="padding:2px 6px;text-align:center">{status_badge}</td>'
            f'<td style="padding:2px 6px;font-size:12px">{inv_text}</td>'
            f"</tr>"
        )

    header = (
        "<tr>"
        '<th style="padding:2px 6px;text-align:left">Robot</th>'
        '<th style="padding:2px 6px;text-align:left">Pos</th>'
        '<th style="padding:2px 6px;text-align:left">HP</th>'
        '<th style="padding:2px 6px;text-align:center">Status</th>'
        '<th style="padding:2px 6px;text-align:left">Inventaire</th>'
        "</tr>"
    )

    with solara.Card(title):
        solara.Markdown(
            f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
            f"<thead>{header}</thead><tbody>{rows_html}</tbody></table>"
        )


@solara.component
def ComparisonTable(model1, model2, version):
    """Side-by-side comparison table replacing the old VersusSummary."""
    _ = version

    counts1 = model1.count_wastes_on_grid()
    counts2 = model2.count_wastes_on_grid()
    step1 = model1.finished_at if model1.finished_at is not None else model1.step_count
    step2 = model2.finished_at if model2.finished_at is not None else model2.step_count

    def status(m):
        if m.finished_at is not None:
            if m.stored_red_waste >= m.expected_stored_red:
                return "Succès"
            return "Deadlock"
        return "En cours..."

    metrics = [
        ("Step", str(step1), str(step2)),
        ("Status", status(model1), status(model2)),
        ("Déchets verts", str(counts1["green"]), str(counts2["green"])),
        ("Déchets jaunes", str(counts1["yellow"]), str(counts2["yellow"])),
        ("Déchets rouges", str(counts1["red"]), str(counts2["red"])),
        ("Stockés / Attendus", f"{model1.stored_red_waste}/{model1.expected_stored_red}",
         f"{model2.stored_red_waste}/{model2.expected_stored_red}"),
        ("Messages", str(model1.message_count), str(model2.message_count)),
    ]

    header = (
        "<tr>"
        '<th style="padding:4px 12px;text-align:left;border-bottom:2px solid #ddd">Métrique</th>'
        '<th style="padding:4px 12px;text-align:center;border-bottom:2px solid #ddd;color:#c62828">Phase 1 (sans com.)</th>'
        '<th style="padding:4px 12px;text-align:center;border-bottom:2px solid #ddd;color:#1b5e20">Phase 2 (avec com.)</th>'
        "</tr>"
    )

    rows_html = ""
    for label, v1, v2 in metrics:
        rows_html += (
            f"<tr>"
            f'<td style="padding:3px 12px;font-weight:600">{label}</td>'
            f'<td style="padding:3px 12px;text-align:center">{v1}</td>'
            f'<td style="padding:3px 12px;text-align:center">{v2}</td>'
            f"</tr>"
        )

    with solara.Card("Comparaison Phase 1 vs Phase 2"):
        solara.Markdown(
            f'<table style="width:100%;border-collapse:collapse;font-size:14px">'
            f"<thead>{header}</thead><tbody>{rows_html}</tbody></table>"
        )


@solara.component
def Legend():
    items = [
        ("#1b5e20", "G", "Robot vert"),
        ("#fbc02d", "Y", "Robot jaune"),
        ("#c62828", "R", "Robot rouge"),
        ("#000000", "KO", "Robot KO"),
        ("#a5d6a7", "g", "Déchet vert"),
        ("#fff59d", "y", "Déchet jaune"),
        ("#ef9a9a", "r", "Déchet rouge"),
        ("#212121", "D", "Zone de stockage"),
        ("#1b5e20", "Bv", "Base verte"),
        ("#f57f17", "By", "Base jaune"),
        ("#b71c1c", "Br", "Base rouge"),
    ]

    html = ""
    for color, symbol, label in items:
        txt_color = "#fff" if color in ["#1b5e20", "#c62828", "#000000", "#212121", "#b71c1c"] else "#111"
        html += (
            f'<span style="display:inline-flex;align-items:center;margin:2px 8px 2px 0">'
            f'<span style="display:inline-flex;align-items:center;justify-content:center;'
            f"width:26px;height:26px;border-radius:5px;"
            f"background:{color};color:{txt_color};"
            f'font-weight:700;font-size:11px;margin-right:4px">{symbol}</span>'
            f'<span style="font-size:13px">{label}</span>'
            f"</span>"
        )

    with solara.Card("Légende"):
        solara.Markdown(f'<div style="display:flex;flex-wrap:wrap;gap:4px">{html}</div>')


# ---------------------------------------------------------
# Charts — split Phase 1 / Phase 2
# ---------------------------------------------------------

def _make_phase_chart(model, title, color_prefix):
    colors = {
        "green": "#4caf50",
        "yellow": "#ffc107",
        "red": "#f44336",
        "stored": "#1565c0",
    }

    fig, ax = plt.subplots(figsize=(6, 3.2))

    steps = model.history["steps"]
    ax.plot(steps, model.history["green"], color=colors["green"], label="Verts sur grille", linewidth=1.5)
    ax.plot(steps, model.history["yellow"], color=colors["yellow"], label="Jaunes sur grille", linewidth=1.5)
    ax.plot(steps, model.history["red"], color=colors["red"], label="Rouges sur grille", linewidth=1.5)
    ax.plot(steps, model.history["stored_red"], color=colors["stored"], label="Rouges stockés", linewidth=2, linestyle="--")

    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel("Step", fontsize=10)
    ax.set_ylabel("Quantité", fontsize=10)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.2)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    fig.tight_layout()
    return fig


@solara.component
def PhaseChart(model, version, title):
    _ = version
    fig = _make_phase_chart(model, title, "")
    solara.FigureMatplotlib(fig)
    plt.close(fig)


@solara.component
def MessagesChart(model1, model2, version):
    """Cumulative messages comparison chart."""
    _ = version

    fig, ax = plt.subplots(figsize=(6, 2.5))

    if model1.history["steps"]:
        ax.plot(model1.history["steps"], model1.history["messages"],
                color="#9e9e9e", label="Phase 1", linewidth=1.5)
    if model2.history["steps"]:
        ax.plot(model2.history["steps"], model2.history["messages"],
                color="#1565c0", label="Phase 2", linewidth=1.5)

    ax.set_title("Messages cumulés", fontsize=12, fontweight="bold")
    ax.set_xlabel("Step", fontsize=10)
    ax.set_ylabel("Messages", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.2)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    fig.tight_layout()

    solara.FigureMatplotlib(fig)
    plt.close(fig)


# ---------------------------------------------------------
# Main page
# ---------------------------------------------------------

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

    solara.Title("Robot Mission V2 - Contamination")

    with solara.Column(gap="16px"):
        solara.Markdown("## Phase 1 (sans communication) vs Phase 2 (avec communication)")
        solara.Markdown(
            f"Seed: **{initial_seed}** | Déchets verts initiaux: **{initial_wastes}** | "
            f"Objectif: **{model1.expected_stored_red}** rouges stockés"
        )

        # Controls
        with solara.Row(gap="10px", style={"align-items": "center"}):
            solara.Button("Step", on_click=step_both, icon_name="mdi-skip-next")
            solara.Button("Reset", on_click=reset_both, icon_name="mdi-refresh")
            solara.Button(
                "Stop" if auto_run else "Auto",
                on_click=toggle_auto,
                icon_name="mdi-stop" if auto_run else "mdi-play",
                color="red" if auto_run else "green",
            )
            solara.SliderFloat(
                label="Vitesse (s/step)",
                value=speed,
                min=0.05,
                max=1.0,
                step=0.05,
                on_value=set_speed,
            )

        # Comparison table
        ComparisonTable(model1, model2, version)

        # Grids side by side
        with solara.Columns([1, 1]):
            with solara.Column():
                GridView(model1, version, "Phase 1 - Grille")
                RobotStatusTable(model1, version, "Phase 1 - Robots")
            with solara.Column():
                GridView(model2, version, "Phase 2 - Grille")
                RobotStatusTable(model2, version, "Phase 2 - Robots")

        # Charts side by side
        with solara.Columns([1, 1]):
            with solara.Column():
                with solara.Card("Phase 1 - Déchets"):
                    PhaseChart(model1, version, "Phase 1 (sans communication)")
            with solara.Column():
                with solara.Card("Phase 2 - Déchets"):
                    PhaseChart(model2, version, "Phase 2 (avec communication)")

        # Messages chart
        with solara.Card("Messages cumulés"):
            MessagesChart(model1, model2, version)

        # Legend
        Legend()

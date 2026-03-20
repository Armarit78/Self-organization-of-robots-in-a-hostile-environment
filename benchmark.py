# ============================================================
# Group: GROUP_NUMBER
# Date: DATE
# Members: MEMBER_1, MEMBER_2, MEMBER_3
# File: benchmark.py
# ============================================================

import csv
import random
import statistics

from model import RobotMission


DEFAULT_PARAMS = dict(
    width=18,
    height=8,
    n_green_robots=3,
    n_yellow_robots=2,
    n_red_robots=2,
    max_steps=2000,
)


def sample_initial_green_wastes(width, height, seed):
    """
    Reproduce the same initial waste-count sampling logic as the model,
    but outside the model so Phase 1 and Phase 2 get the exact same setup.
    """
    rng = random.Random(seed)
    z1_width = width // 3
    z1_capacity = z1_width * height
    return rng.randint(12, max(12, z1_capacity // 2))


def avg(values):
    return statistics.mean(values) if values else 0.0


def rate_true(rows, key):
    return sum(1 for row in rows if row[key]) / len(rows) if rows else 0.0


def run_one_simulation(seed, communication_enabled, n_initial_green_wastes, max_steps):
    model = RobotMission(
        width=DEFAULT_PARAMS["width"],
        height=DEFAULT_PARAMS["height"],
        n_green_robots=DEFAULT_PARAMS["n_green_robots"],
        n_yellow_robots=DEFAULT_PARAMS["n_yellow_robots"],
        n_red_robots=DEFAULT_PARAMS["n_red_robots"],
        seed=seed,
        n_initial_green_wastes=n_initial_green_wastes,
        communication_enabled=communication_enabled,
        max_steps=max_steps,
    )

    while not model.is_finished() and model.step_count < max_steps:
        model.step()

    counts = model.count_wastes_on_grid()
    steps = model.finished_at if model.finished_at is not None else model.step_count

    # With the current model logic, success/finish is reached as soon as
    # enough red waste has been stored.
    finished = model.stored_red_waste >= model.expected_stored_red
    success = finished

    completion_ratio = (
        model.stored_red_waste / model.expected_stored_red
        if model.expected_stored_red > 0
        else 0.0
    )
    efficiency = model.stored_red_waste / steps if steps > 0 else 0.0

    return {
        "seed": seed,
        "phase": "phase2_comm" if communication_enabled else "phase1_no_comm",
        "communication_enabled": communication_enabled,
        "initial_green_wastes": model.initial_green_wastes,
        "finished": finished,
        "success": success,
        "steps": steps,
        "stored_red": model.stored_red_waste,
        "expected_stored_red": model.expected_stored_red,
        "completion_ratio": round(completion_ratio, 4),
        "efficiency": round(efficiency, 6),
        "messages": model.message_count,
        "remaining_green": counts["green"],
        "remaining_yellow": counts["yellow"],
        "remaining_red": counts["red"],
    }


def write_detailed_csv(rows, filename):
    fieldnames = [
        "seed",
        "phase",
        "communication_enabled",
        "initial_green_wastes",
        "finished",
        "success",
        "steps",
        "stored_red",
        "expected_stored_red",
        "completion_ratio",
        "efficiency",
        "messages",
        "remaining_green",
        "remaining_yellow",
        "remaining_red",
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary_csv(rows, filename):
    phase1 = [row for row in rows if row["phase"] == "phase1_no_comm"]
    phase2 = [row for row in rows if row["phase"] == "phase2_comm"]

    summary_rows = [
        {
            "phase": "phase1_no_comm",
            "avg_initial_green_wastes": round(avg([r["initial_green_wastes"] for r in phase1]), 4),
            "avg_steps": round(avg([r["steps"] for r in phase1]), 4),
            "avg_stored_red": round(avg([r["stored_red"] for r in phase1]), 4),
            "avg_expected_stored_red": round(avg([r["expected_stored_red"] for r in phase1]), 4),
            "avg_completion_ratio": round(avg([r["completion_ratio"] for r in phase1]), 4),
            "avg_efficiency": round(avg([r["efficiency"] for r in phase1]), 6),
            "avg_messages": round(avg([r["messages"] for r in phase1]), 4),
            "finish_rate": round(rate_true(phase1, "finished"), 4),
            "success_rate": round(rate_true(phase1, "success"), 4),
        },
        {
            "phase": "phase2_comm",
            "avg_initial_green_wastes": round(avg([r["initial_green_wastes"] for r in phase2]), 4),
            "avg_steps": round(avg([r["steps"] for r in phase2]), 4),
            "avg_stored_red": round(avg([r["stored_red"] for r in phase2]), 4),
            "avg_expected_stored_red": round(avg([r["expected_stored_red"] for r in phase2]), 4),
            "avg_completion_ratio": round(avg([r["completion_ratio"] for r in phase2]), 4),
            "avg_efficiency": round(avg([r["efficiency"] for r in phase2]), 6),
            "avg_messages": round(avg([r["messages"] for r in phase2]), 4),
            "finish_rate": round(rate_true(phase2, "finished"), 4),
            "success_rate": round(rate_true(phase2, "success"), 4),
        },
    ]

    fieldnames = list(summary_rows[0].keys())

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)


def write_paired_csv(rows, filename):
    by_seed = {}
    for row in rows:
        by_seed.setdefault(row["seed"], {})
        by_seed[row["seed"]][row["phase"]] = row

    paired_rows = []
    for seed, data in sorted(by_seed.items()):
        if "phase1_no_comm" not in data or "phase2_comm" not in data:
            continue

        p1 = data["phase1_no_comm"]
        p2 = data["phase2_comm"]

        paired_rows.append(
            {
                "seed": seed,
                "initial_green_wastes": p1["initial_green_wastes"],
                "steps_phase1": p1["steps"],
                "steps_phase2": p2["steps"],
                "delta_steps": p2["steps"] - p1["steps"],
                "stored_red_phase1": p1["stored_red"],
                "stored_red_phase2": p2["stored_red"],
                "delta_stored_red": p2["stored_red"] - p1["stored_red"],
                "messages_phase1": p1["messages"],
                "messages_phase2": p2["messages"],
                "delta_messages": p2["messages"] - p1["messages"],
                "completion_ratio_phase1": p1["completion_ratio"],
                "completion_ratio_phase2": p2["completion_ratio"],
                "efficiency_phase1": p1["efficiency"],
                "efficiency_phase2": p2["efficiency"],
                "finished_phase1": p1["finished"],
                "finished_phase2": p2["finished"],
                "success_phase1": p1["success"],
                "success_phase2": p2["success"],
            }
        )

    fieldnames = list(paired_rows[0].keys()) if paired_rows else [
        "seed",
        "initial_green_wastes",
        "steps_phase1",
        "steps_phase2",
        "delta_steps",
        "stored_red_phase1",
        "stored_red_phase2",
        "delta_stored_red",
        "messages_phase1",
        "messages_phase2",
        "delta_messages",
        "completion_ratio_phase1",
        "completion_ratio_phase2",
        "efficiency_phase1",
        "efficiency_phase2",
        "finished_phase1",
        "finished_phase2",
        "success_phase1",
        "success_phase2",
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(paired_rows)


def print_summary(rows):
    phase1 = [row for row in rows if row["phase"] == "phase1_no_comm"]
    phase2 = [row for row in rows if row["phase"] == "phase2_comm"]

    print("\n=== BENCHMARK SUMMARY ===")
    print(f"Phase 1 - avg steps: {avg([r['steps'] for r in phase1]):.2f}")
    print(f"Phase 2 - avg steps: {avg([r['steps'] for r in phase2]):.2f}")
    print(f"Phase 1 - avg stored red: {avg([r['stored_red'] for r in phase1]):.2f}")
    print(f"Phase 2 - avg stored red: {avg([r['stored_red'] for r in phase2]):.2f}")
    print(f"Phase 1 - avg completion ratio: {avg([r['completion_ratio'] for r in phase1]):.4f}")
    print(f"Phase 2 - avg completion ratio: {avg([r['completion_ratio'] for r in phase2]):.4f}")
    print(f"Phase 1 - avg efficiency: {avg([r['efficiency'] for r in phase1]):.6f}")
    print(f"Phase 2 - avg efficiency: {avg([r['efficiency'] for r in phase2]):.6f}")
    print(f"Phase 1 - avg messages: {avg([r['messages'] for r in phase1]):.2f}")
    print(f"Phase 2 - avg messages: {avg([r['messages'] for r in phase2]):.2f}")
    print(f"Phase 1 - finish rate: {rate_true(phase1, 'finished') * 100:.1f}%")
    print(f"Phase 2 - finish rate: {rate_true(phase2, 'finished') * 100:.1f}%")
    print(f"Phase 1 - success rate: {rate_true(phase1, 'success') * 100:.1f}%")
    print(f"Phase 2 - success rate: {rate_true(phase2, 'success') * 100:.1f}%")

    avg_steps_p1 = avg([r["steps"] for r in phase1])
    avg_steps_p2 = avg([r["steps"] for r in phase2])

    if avg_steps_p1 > 0:
        improvement = ((avg_steps_p1 - avg_steps_p2) / avg_steps_p1) * 100
        print(f"Phase 2 improvement vs Phase 1: {improvement:.2f}% fewer steps on average")


def run_benchmark(n_runs=30, seed_start=100):
    rows = []

    for i in range(n_runs):
        seed = seed_start + i

        # Same initial waste count for both phases
        shared_initial_green_wastes = sample_initial_green_wastes(
            DEFAULT_PARAMS["width"],
            DEFAULT_PARAMS["height"],
            seed,
        )

        row_p1 = run_one_simulation(
            seed=seed,
            communication_enabled=False,
            n_initial_green_wastes=shared_initial_green_wastes,
            max_steps=DEFAULT_PARAMS["max_steps"],
        )

        row_p2 = run_one_simulation(
            seed=seed,
            communication_enabled=True,
            n_initial_green_wastes=shared_initial_green_wastes,
            max_steps=DEFAULT_PARAMS["max_steps"],
        )

        rows.append(row_p1)
        rows.append(row_p2)

    write_detailed_csv(rows, "results/benchmark_results_detailed.csv")
    write_summary_csv(rows, "results/benchmark_results_summary.csv")
    write_paired_csv(rows, "results/benchmark_results_paired.csv")

    print_summary(rows)

    print("\nFiles saved:")
    print("- results/benchmark_results_detailed.csv")
    print("- results/benchmark_results_summary.csv")
    print("- results/benchmark_results_paired.csv")


if __name__ == "__main__":
    run_benchmark(n_runs=30, seed_start=100)
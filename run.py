# ============================================================
# Group: GROUP_NUMBER
# Date: DATE
# Members: MEMBER_1, MEMBER_2, MEMBER_3
# File: run.py
# ============================================================

import os
import time

from model import RobotMission
from server import render


def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")


def main():
    model = RobotMission(
        width=18,
        height=8,
        n_green_robots=3,
        n_yellow_robots=2,
        n_red_robots=2,
        n_initial_green_wastes=24,
        seed=42
    )

    max_steps = 200

    for _ in range(max_steps):
        clear_terminal()
        print(render(model))

        if model.is_finished():
            print("\nMission complete.")
            break

        model.step()
        time.sleep(0.15)

    clear_terminal()
    print(render(model))
    print("\nEnd of simulation.")


if __name__ == "__main__":
    main()
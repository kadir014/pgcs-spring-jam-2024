#import ez_profile
import os; os.environ["PY_USED_FREEZER"] = "none"

from engine import Engine
from engine.path import source_path
from scenes.game import Game
from scenes.settings import Settings
from scenes.menu import Menu


if __name__ == "__main__":
    cwd = os.getcwd()
    settings_path = os.path.join(cwd, "settings.cfg")
    if not os.path.exists(settings_path):
        with open(settings_path, "w") as f:
            f.write("""
[Engine]
title = Thermal Trials  -  PGCS Spring Jam 2024
max_fps = 60
forced_width = 1280
forced_height = 720
hardware_scaling = on
fullscreen = off
master_volume = 1.0

[Graphics]
quality = 3
            """)

    engine = Engine(settings_path)

    engine.add_scene(Game)
    engine.add_scene(Settings)
    engine.add_scene(Menu)

    engine.run()
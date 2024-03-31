#import ez_profile
import os; os.environ["PY_USED_FREEZER"] = "none"

from engine import Engine
from engine.path import source_path
from scenes.game import Game
from scenes.menu import Menu


if __name__ == "__main__":
    engine = Engine(source_path("settings.cfg"))

    engine.add_scene(Game)

    engine.run()
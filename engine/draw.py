from typing import TYPE_CHECKING

import sys
import platform
from functools import lru_cache

import pygame
import pymunk

if TYPE_CHECKING:
    from .engine import Engine


@lru_cache()
def render_shadow_text(
        font: pygame.Font,
        text: str,
        color: tuple[float, float, float],
        shadow_offset: int = 1
        ) -> pygame.Surface:
    """
    Render text with shadow.

    Parameters
    ----------
    @param font Font object
    @param text Text to draw
    @param color Color of text
    @param shadow_offset Distance of shadow from the text
    """
    
    shadow = font.render(text, True, (0, 0, 0)).convert_alpha()

    offsets = (
        (shadow_offset - shadow_offset, shadow_offset                ),
        (shadow_offset + shadow_offset, shadow_offset                ),
        (shadow_offset,                 shadow_offset + shadow_offset),
        (shadow_offset,                 shadow_offset - shadow_offset)
    )

    surf = pygame.Surface(
        (shadow.get_width() + shadow_offset * 2, shadow.get_height() + shadow_offset * 2),
        pygame.SRCALPHA
    ).convert_alpha()

    for p in offsets:
        surf.blit(shadow, p)

    surf.blit(font.render(text, True, color), (shadow_offset, shadow_offset))

    return surf


def draw_shadow_text(
        surface: pygame.Surface,
        font: pygame.Font,
        text: str,
        pos: tuple[int, int],
        color: tuple[float, float, float],
        shadow_offset: int = 1
        ) -> None:
    """
    Draw text with shadow on a Pygame surface.

    Parameters
    ----------
    @param font Font object
    @param text Text to draw
    @param pos Position on surface
    @param color Color of text
    @param shadow_offset Distance of shadow from the text
    """

    surface.blit(render_shadow_text(font, text, color, shadow_offset), pos)


def draw_debug_ui(engine: "Engine", minimal: bool = False) -> None:
    """ 
    Render debug UI.

    Parameters
    ----------
    @param engine Engine instance.
    @param minimal Show only FPS.
    """

    font = engine.asset_manager.get_font("FiraCode-Bold", 12)

    y_gap = 16
    row_start = 65
    row_gap = 45
    label_color = (255, 255, 255)
    avg_color = (255, 241, 115)
    min_color = (121, 255, 94)
    max_color = (255, 101, 87)
    cpu_color = (112, 212, 255)
    version_color = (138, 255, 208)

    if minimal:
        bg = pygame.Surface((70, 26), pygame.SRCALPHA).convert_alpha()
        bg.fill((0, 0, 0, 130))

        draw_shadow_text(
            bg,
            font,
            "FPS", (5, 5 + y_gap * 0),
            label_color
        )
        draw_shadow_text(
            bg,
            font,
            str(round(engine.stats["fps"]["avg"])),
            (row_start + row_gap * 0 - 30, 5 + y_gap * 0),
            avg_color
        )

    else:
        bg = pygame.Surface((305, 190), pygame.SRCALPHA).convert_alpha()
        bg.fill((0, 0, 0, 130))

        # Draw FPS stats
        draw_shadow_text(
            bg,
            font,
            "FPS", (5, 5 + y_gap * 0),
            label_color
        )
        draw_shadow_text(
            bg,
            font,
            str(round(engine.stats["fps"]["avg"])),
            (row_start + row_gap * 0, 5 + y_gap * 0),
            avg_color
        )
        draw_shadow_text(
            bg,
            font,
            str(round(engine.stats["fps"]["max"])),
            (row_start + row_gap * 1, 5 + y_gap * 0),
            min_color
        )
        draw_shadow_text(
            bg,
            font,
            str(round(engine.stats["fps"]["min"])),
            (row_start + row_gap * 2, 5 + y_gap * 0),
            max_color
        )

        # Draw frame time stats
        draw_shadow_text(
            bg,
            font,
            "Frame", (5, 5 + y_gap * 1),
            label_color
        )
        draw_shadow_text(
            bg,
            font,
            str(round(engine.stats["frame"]["avg"] * 1000, 2)),
            (row_start + row_gap * 0, 5 + y_gap * 1),
            avg_color
        )
        draw_shadow_text(
            bg,
            font,
            str(round(engine.stats["frame"]["min"] * 1000, 2)),
            (row_start + row_gap * 1, 5 + y_gap * 1),
            min_color
        )
        draw_shadow_text(
            bg,
            font,
            str(round(engine.stats["frame"]["max"] * 1000, 2)),
            (row_start + row_gap * 2, 5 + y_gap * 1),
            max_color
        )
        draw_shadow_text(
            bg,
            font,
            "ms",
            (row_start + row_gap * 3, 5 + y_gap * 1),
            label_color
        )

        # Draw render time stats
        draw_shadow_text(
            bg,
            font,
            "Render", (5, 5 + y_gap * 2),
            label_color
        )
        draw_shadow_text(
            bg,
            font,
            str(round(engine.stats["render"]["avg"] * 1000, 2)),
            (row_start + row_gap * 0, 5 + y_gap * 2),
            avg_color
        )
        draw_shadow_text(
            bg,
            font,
            str(round(engine.stats["render"]["min"] * 1000, 2)),
            (row_start + row_gap * 1, 5 + y_gap * 2),
            min_color
        )
        draw_shadow_text(
            bg,
            font,
            str(round(engine.stats["render"]["max"] * 1000, 2)),
            (row_start + row_gap * 2, 5 + y_gap * 2),
            max_color
        )
        draw_shadow_text(
            bg,
            font,
            "ms",
            (row_start + row_gap * 3, 5 + y_gap * 2),
            label_color
        )

        # Draw update time stats
        draw_shadow_text(
            bg,
            font,
            "Update", (5, 5 + y_gap * 3),
            label_color
        )
        draw_shadow_text(
            bg,
            font,
            str(round(engine.stats["update"]["avg"] * 1000, 2)),
            (row_start + row_gap * 0, 5 + y_gap * 3),
            avg_color
        )
        draw_shadow_text(
            bg,
            font,
            str(round(engine.stats["update"]["min"] * 1000, 2)),
            (row_start + row_gap * 1, 5 + y_gap * 3),
            min_color
        )
        draw_shadow_text(
            bg,
            font,
            str(round(engine.stats["update"]["max"] * 1000, 2)),
            (row_start + row_gap * 2, 5 + y_gap * 3),
            max_color
        )
        draw_shadow_text(
            bg,
            font,
            "ms",
            (row_start + row_gap * 3, 5 + y_gap * 3),
            label_color
        )

        # Draw hardware info
        draw_shadow_text(
            bg,
            font,
            engine.cpu_info["name"],
            (5, 5 + y_gap * 4),
            cpu_color
        )

        draw_shadow_text(
            bg,
            font,
            "Platform",
            (5, 5 + y_gap * 5),
            label_color
        )

        draw_shadow_text(
            bg,
            font,
            engine.platform,
            (70, 5 + y_gap * 5),
            avg_color
        )

        # Display info
        draw_shadow_text(
            bg,
            font,
            "Display",
            (5, 5 + y_gap * 6),
            label_color
        )
        draw_shadow_text(
            bg,
            font,
            f"{engine.window_width}x{engine.window_height}",
            (60, 5 + y_gap * 6),
            avg_color
        )

        # Draw version info
        is_python_64bit = sys.maxsize > 2**32
        draw_shadow_text(
            bg,
            font,
            "Python",
            (5, 5 + y_gap * 7),
            label_color
        )
        draw_shadow_text(
            bg,
            font,
            f"{platform.python_version()}, {('32', '64')[is_python_64bit]}-bit",
            (row_start - 12, 5 + y_gap * 7),
            version_color
        )

        draw_shadow_text(
            bg,
            font,
            "Pygame",
            (5, 5 + y_gap * 8),
            label_color
        )
        draw_shadow_text(
            bg,
            font,
            str(engine.pygame_version),
            (row_start - 12, 5 + y_gap * 8),
            version_color
        )

        draw_shadow_text(
            bg,
            font,
            "SDL",
            (5, 5 + y_gap * 9),
            label_color
        )
        draw_shadow_text(
            bg,
            font,
            str(engine.sdl_version),
            (row_start - 12, 5 + y_gap * 9),
            version_color
        )

        draw_shadow_text(
            bg,
            font,
            "Pymunk",
            (5, 5 + y_gap * 10),
            label_color
        )
        draw_shadow_text(
            bg,
            font,
            f"{pymunk.version} ({pymunk.chipmunk_version[:5]})",
            (row_start - 12, 5 + y_gap * 10),
            version_color
        )

    engine.display.blit(bg, (0, 0))
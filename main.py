import pyglet
import os
from pathlib import Path

from game_window import GameWindow


if __name__ == '__main__':

    mario_graphics_dir = Path( '/home/seph/game_practice/mario_64_graphics' )

    font_filename = 'super-mario-64.ttf'
    font_name = 'Super Mario 64'
    font_path = str( ( mario_graphics_dir / 'fonts' / font_filename ).resolve() )
    pyglet.font.add_file( font_path )

    screenshot_dir = mario_graphics_dir / 'screenshots'
    os.makedirs( screenshot_dir, exist_ok=True )

    game_window = GameWindow( mario_graphics_dir, fullscreen=False, y_inv=False, vsync=False, resizable=True, load_textures=True, wireframe=False, load_skyboxes=True, original_res=False, show_fps=False, font=font_name )

    ## Main game loop
    pyglet.app.run()

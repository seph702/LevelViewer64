import pyglet
import os
import argparse
from pathlib import Path

from game_window import GameWindow


if __name__ == '__main__':

    description = 'Level Viewer 64\n\nA level viewer for Mario 64.\n\nExample usages:\npython3 main.py -fs -msaa 16\npython3 main.py -res 1920 1080\npython3 main.py -yinv -fs -msaa 4\n\nNote: the default is 1280x720 resolution with no MSAA.  16x MSAA is the ideal way to play and most modern GPUs support it.  However, if you experience graphical or gameplay issues, try reducing MSAA until the game works properly.'
    parser = argparse.ArgumentParser( description=description, formatter_class=argparse.RawTextHelpFormatter )
    parser.add_argument( '-fs', '--fullscreen', action='store_true', help='enable fullscreen mode' )
    parser.add_argument( '-res', '--resolution', nargs=2, type=int, metavar=( 'x', 'y' ), default=[1280, 720], help='resolution of the game window (default: 1280x720)' )
    parser.add_argument( '-msaa', type=int, metavar='samples', help='number of MSAA samples per pixel (default: 1)', default=1 )
    parser.add_argument( '-yinv', '--invert_y', action='store_true', help='invert the y-axis on the mouse' )
    args = parser.parse_args()

    fullscreen = args.fullscreen
    resolution = args.resolution
    msaa = args.msaa
    yinv = args.invert_y

    mario_graphics_dir = Path( os.path.realpath( __file__ ) ).parent

    font_filename = 'super-mario-64.ttf'
    font_name = 'Super Mario 64'
    font_path = str( ( mario_graphics_dir / 'fonts' / font_filename ).resolve() )
    pyglet.font.add_file( font_path )


    game_window = GameWindow( mario_graphics_dir, fullscreen=fullscreen, resolution=resolution, y_inv=yinv, vsync=False, msaa=msaa, resizable=True, show_fps=False, font=font_name )

    ## Main game loop
    pyglet.app.run()

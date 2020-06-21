from pathlib import Path
from distutils.version import LooseVersion
import os
import sys

try:
    import pyglet
except:
    print( "Please install pyglet for python.  This project uses pyglet for windowing and as an OpenGL wrapper.  You can install it using:\npip install pyglet\n" )
    sys.exit()
assert LooseVersion( pyglet.version ) > LooseVersion( '1.5.4' ), "pyglet must be at least version 1.5.4.  Please upgrade your version of pyglet."
assert LooseVersion( pyglet.version ) != LooseVersion( '1.5.6' ), "pyglet 1.5.6 is a broken release and cannot run this program.  Please either upgrade to a newer version of pyglet or downgrade to 1.5.5."

try:
    import PIL
except:
    print( "Please install Pillow for python.  This project uses Pillow for a slight bit of image manipulation (namely editing the skyboxes).  You can install it using:\npip install Pillow\n" )
    sys.exit()

try:
    import numpy
except:
    print( "Please install numpy for python.  This project uses numpy as the backend for its 3D matrix math.  You can install it using:\npip install numpy\n" )
    sys.exit()

from parsers import texture_parser
from parsers import model_id_parser
from parsers import level_script_parser
from parsers import gfx_from_geo_parser
from parsers import paintings_parser
from parsers import model_parser
from parsers import skybox_extender
from parsers import geo_parser
from parsers import level_fixes
from parsers import movtex_tri_parser




mario_source_dir = Path( '' )
while not os.path.isfile( mario_source_dir / 'extract_assets.py' ):
    mario_source_dir = Path( input( 'Please enter the path of the sm64 source code directory.  This is the directory in which extract_assets.py is located.\nFor Windows, the path should be formatted like the following example:\nC:/Users/Me/mario\n(Note the direction of the slashes.)\n\nFor Linux, the path should be formatted like the following example:\n/home/Me/mario\n\n>' ) )

if not os.path.isfile( mario_source_dir / 'textures' / 'skyboxes' / 'water.png' ):
    print( "Located the sm64 source directory, however textures are missing.  Please run the extract_assets.py script in that directory on your US version baserom." )
    sys.exit()

mario_graphics_dir = Path( os.path.realpath( __file__ ) ).parent
parser_dir = mario_graphics_dir / 'parsers'
pickle_dir = mario_graphics_dir / 'pickles'



print( "Beginning setup.\n" )

os.makedirs( mario_graphics_dir / 'pickles', exist_ok=True )

print( "Parsing textures and building the texture dictionary.  This may take a minute..." )
texture_parser.main( mario_source_dir, pickle_dir )
print( "\n", end='' )

print( "Parsing models and creating model dictionaries." )
model_id_parser.main( mario_source_dir, pickle_dir )
print( "\n", end='' )

print( "Parsing level scripts." )
level_script_parser.main( mario_source_dir, pickle_dir )
print( "\n", end='' )

print( "Parsing gfx data called from level geo." )
gfx_from_geo_parser.main( mario_source_dir, pickle_dir )
print( "\n", end='' )

print( "Parsing gfx data called from paintings." )
paintings_parser.main( mario_source_dir, pickle_dir )
print( "\n", end='' )

print( "Parsing vertex, triangle, and draw data." )
model_parser.main( mario_source_dir, pickle_dir )
print( "\n", end='' )

print( "Converting skyboxes from 248x248 pixels to 256x256." )
skybox_extender.main( mario_source_dir, mario_graphics_dir )
print( "\n", end='' )

print( "Parsing moving texture data." )
movtex_tri_parser.main( mario_source_dir, pickle_dir )
print( "\n", end='' )

print( "Parsing geo data." )
geo_parser.main( mario_source_dir, pickle_dir )
print( "\n", end='' )

print( "Performing level fixes." )
level_fixes.main( mario_source_dir, pickle_dir )
print( "\n", end='' )

print( "Setup complete!  Run main.py and have fun!" )

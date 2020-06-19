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


mario_source_dir = Path( '' )
while not os.path.isfile( mario_source_dir / 'extract_assets.py' ):
    mario_source_dir = Path( input( 'Please enter the path of the sm64 source code directory.  This is the directory in which extract_assets.py is located.\nFor Windows, the path should be formatted like the following example:\nC:/Users/Me/mario\n(Note the direction of the slashes.)\n\nFor Linux, the path be formatted like the following example:\n/home/Me/mario\n\n>' ) )

if not os.path.isfile( mario_source_dir / 'textures' / 'skyboxes' / 'water.png' ):
    print( "Located the sm64 source directory, however textures are missing.  Please run the extract_assets.py script in that directory on your US version baserom." )
    sys.exit()

mario_graphics_dir = Path( os.path.realpath( __file__ ) ).parent
parser_dir = mario_graphics_dir / 'parsers'
pickle_dir = mario_graphics_dir / 'pickles'

############################

def fix_variable_lines_in_main( filepath, variable_arr ):
    """variable_arr is an array of arrays, where each subarray is of length two and contains two strings.  The first string is a variable name and the second string is the new value to set the variable to."""

    with open( filepath, 'r' ) as f:
        textlines = f.read().splitlines()

    for ind, line in enumerate( textlines ):
        if '__name__' in line and '__main__' in line:
            main_ind = ind
            break

    ind = main_ind
    for i in range( len( variable_arr ) ):
        variable_arr[ i ][ 0 ] += ' ='
    while ind < len( textlines ):
        curr_line = textlines[ ind ]
        for each_variable in variable_arr:
            if each_variable[ 0 ] in curr_line:
                textlines[ ind ] = curr_line[ : curr_line.find( '=' ) + 1 ] + ' ' + each_variable[ 1 ]

        ind += 1

    with open( filepath, 'w' ) as f:
        for line in textlines:
            f.write( line )
            f.write( '\n' )



############################

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

## Edit main.py to replace mario_source_dir and mario_graphics_dir variables with the variables at the top of this file.
print( "Editing scripts to use user supplied source code path." )
source_path_str = repr( mario_source_dir ).split( '\'' )[ 1 ]
new_source_str = "Path( '" + source_path_str + "' )"
graphics_path_str = repr( mario_graphics_dir ).split( '\'' )[ 1 ]
new_graphics_str = "Path( '" + graphics_path_str + "' )"

variables_to_fix = [ [ 'mario_source_dir', new_source_str ], [ 'mario_graphics_dir', new_graphics_str ] ]

print( "Editing main.py." )
fix_variable_lines_in_main( mario_graphics_dir / 'main.py', variables_to_fix )
print( "Editing model_id_parser.py." )
fix_variable_lines_in_main( parser_dir / 'model_id_parser.py', variables_to_fix )
print( "Editing texture_parser.py." )
fix_variable_lines_in_main( parser_dir / 'texture_parser.py', variables_to_fix )
print( "Editing level_script_parser.py." )
fix_variable_lines_in_main( parser_dir / 'level_script_parser.py', variables_to_fix )
print( "Editing paintings_parser.py." )
fix_variable_lines_in_main( parser_dir / 'paintings_parser.py', variables_to_fix )
print( "Editing model_parser.py." )
fix_variable_lines_in_main( parser_dir / 'model_parser.py', variables_to_fix )
print( "Editing skybox_extender.py." )
fix_variable_lines_in_main( parser_dir / 'skybox_extender.py', variables_to_fix )
print( "Editing gfx_from_geo_parser.py." )
fix_variable_lines_in_main( parser_dir / 'gfx_from_geo_parser.py', variables_to_fix )
print( "Editing movtex_tri_parser.py." )
fix_variable_lines_in_main( parser_dir / 'movtex_tri_parser.py', variables_to_fix )
print( "Editing geo_parser.py." )
fix_variable_lines_in_main( parser_dir / 'geo_parser.py', variables_to_fix )
print( "Editing level_fixes.py." )
fix_variable_lines_in_main( parser_dir / 'level_fixes.py', variables_to_fix )
print( "Editing complete.\n" )

print( "Setup complete!  Run main.py and have fun!" )

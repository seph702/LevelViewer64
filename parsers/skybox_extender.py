from PIL import Image
import numpy as np
import os
from pathlib import Path

def main( mario_source_dir, mario_graphics_dir ):

    mario_skybox_dir = mario_source_dir / 'textures' / 'skyboxes'

    for im_filepath in mario_skybox_dir.glob( '*.png' ):
    
        im_filename = str( im_filepath.resolve() )
        im = Image.open( im_filename )
        short_filename = im_filepath.stem
        print( 'Processing skybox:', short_filename )
    
        width = im.width
        height = im.height
    
        if width % 31 == 0 and height % 31 == 0:
            im_arr = np.asarray( im )
    
            rows = width // 31
            cols = height // 31
            out_arr = np.zeros( ( 32 * rows, 32 * cols, 4 ), 'uint8' )
    
            for y in range( cols ):
                for x in range( rows ):
                    for inY in range( 32 ):
                        for inX in range( 32 ):
                            original_RGBA = im_arr[ ( inX + 31 * x ) % width, ( inY + 31 * y ) % height ]
                            out_arr[ ( inX + 32 * x ), ( inY + 32 * y ) ] = original_RGBA
    
            os.makedirs( mario_graphics_dir / 'skyboxes', exist_ok=True )
            out_dir = str( ( mario_graphics_dir / 'skyboxes' / ( short_filename + '.png' ) ).resolve() )
            out_img = Image.fromarray( out_arr, 'RGBA' )
            out_img.save( out_dir, 'PNG' )

    print( 'Skybox files extended and written to mario_graphics_dir/skyboxes.' )


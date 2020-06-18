from pathlib import Path
import pickle

from .level_script_parser import process_line


## This parser will generate a dictionary that has Gfx names as keys for all Gfx that are called directly from geo files.  The values will simply be True, because we just want an O(1) way to see if a particular Gfx is called from geo.

def main( mario_source_dir, mario_graphics_dir ):

    gfxs_called_from_geo = {}
    geo_filepaths = mario_source_dir.glob( '**/geo.inc.c' )


    for each_geo_filepath in geo_filepaths:
        with open( each_geo_filepath, 'r' ) as f:
            geo_txt = f.read()

        geo_lines = [ each_line.strip() for each_line in geo_txt.split( '\n' ) ]
        for each_line in geo_lines:
            if 'GEO_TRANSLATE_ROTATE_WITH_DL' in each_line \
                or 'GEO_TRANSLATE_WITH_DL' in each_line \
                or 'GEO_ROTATE_WITH_DL' in each_line \
                or 'GEO_ROTATE_Y_WITH_DL' in each_line \
                or 'GEO_TRANSLATE_NODE_WITH_DL' in each_line \
                or 'GEO_ROTATION_NODE_WITH_DL' in each_line \
                or 'GEO_ANIMATED_PART' in each_line \
                or 'GEO_BILLBOARD_WITH_PARAMS_AND_DL' in each_line \
                or 'GEO_DISPLAY_LIST' in each_line \
                or 'GEO_SCALE_WITH_DL' in each_line:
                    *_, display_list = process_line( each_line )
                    if display_list != 'NULL':
                        gfxs_called_from_geo[ display_list ] = True
                    

    with open( mario_graphics_dir / 'gfxs_called_from_geo.pickle', 'wb' ) as f:
        pickle.dump( gfxs_called_from_geo, f, pickle.HIGHEST_PROTOCOL )

    print( 'gfxs_called_from_geo written to file.' )



if __name__ == "__main__":

    mario_source_dir = Path( "/home/seph/mario_source/sm64" )
    mario_graphics_dir = Path( "/home/seph/game_practice/mario_64_graphics" )
    main( mario_source_dir, mario_graphics_dir )

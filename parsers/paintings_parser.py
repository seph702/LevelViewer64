from pathlib import Path
import pickle

from .level_script_parser import process_line


class Painting():
    def __init__( self, name, code ):
        self.name = name
        self.id = None
        self.pitch = None
        self.yaw = None
        self.posx = None
        self.posy = None
        self.posz = None
        self.normal_dl = None
        self.alpha = None
        self.layer = None
        self.size = None
        self.parse_painting( code )

    def parse_painting( self, code ):
        str_for_process_line = code.replace( '{', '(' )
        str_for_process_line = str_for_process_line.replace( '}', ')' )
        str_for_process_line = str_for_process_line.replace( '\n', '' )
        painting_arguments = process_line( str_for_process_line )
        self.id = painting_arguments[ 0 ]
        self.pitch = painting_arguments[ 7 ]
        self.yaw = painting_arguments[ 8 ]
        self.posx = painting_arguments[ 9 ]
        self.posy = painting_arguments[ 10 ]
        self.posz = painting_arguments[ 11 ]
        self.normal_dl = painting_arguments[ 27 ]
        self.alpha = painting_arguments[ 34 ]
        if self.alpha == 255:
            self.layer = 'LAYER_OPAQUE'
        else:
            self.layer = 'LAYER_TRANSPARENT'
        self.size = painting_arguments[ 38 ]


def main( mario_source_dir, mario_graphics_dir ):

    pathlist = [ each_path for each_path in mario_source_dir.glob( '**/painting.inc.c' ) ]
    
    paintings_dict = {}
    
    for each_path in pathlist:
        with open( each_path, 'r' ) as f:
            source = f.read()
    
        structs = source.split( ';' )
    
        for each_struct in structs:
            if 'struct Painting' in each_struct:
                name_start = each_struct.find( 'struct Painting' ) + len( 'struct Painting' ) + 1
                name_end = each_struct.find( '=' )
                name = each_struct[ name_start : name_end ].strip()
                paintings_dict[ name ] = Painting( name, each_struct[ name_end + 1 : ] )
    
    
    gfxs_called_from_paintings = {}
    
    for each_painting in paintings_dict.keys():
        gfxs_called_from_paintings[ paintings_dict[ each_painting ].normal_dl ] = True


    with open( mario_graphics_dir / 'paintings.pickle', 'wb' ) as f:
        pickle.dump( paintings_dict, f, pickle.HIGHEST_PROTOCOL )

    with open( mario_graphics_dir / 'gfxs_called_from_paintings.pickle', 'wb' ) as f:
        pickle.dump( gfxs_called_from_paintings, f, pickle.HIGHEST_PROTOCOL )

    print( "Saved paintings to file." )



from pathlib import Path
import pickle

from .level_script_parser import process_line
from .model_parser import get_name, RenderSettings, Light, Vertex, Vtx, Gfx, GfxDrawList


def convert_to_twos_complement( num, bits ):
    if num < 0:
        return 2**bits + num
    else:
        return num


def get_movtex_name( code ):
    """Takes in a block of code corresponding to a struct of either lights, Vtx, or Gfx, and gets the name of the struct."""
    lines = code.split( '\n' )
    for each_line in lines:
        if '//' in each_line:
            each_line = each_line[ : each_line.find( '//' ) ]

        if 'Movtex ' in each_line or 'Gfx ' in each_line:
            if '[]' in each_line:
                temp_line = [ each_word.strip() for each_word in each_line.split( '[]' ) ]
                temp_line = temp_line[ 0 ].split( ' ' )
                return temp_line[ -1 ]



class Movtex_Tri():

    movtex_texture_dict = { 'TEXTURE_WATER' : 'texture_waterbox_water', 'TEXTURE_MIST' : 'texture_waterbox_mist', 'TEXTURE_JRB_WATER' : 'texture_waterbox_jrb_water', 'TEXTURE_UNK_WATER' : 'texture_waterbox_unknown_water', 'TEXTURE_LAVA' : 'texture_waterbox_lava', 'TEX_QUICKSAND_SSL' : 'ssl_quicksand', 'TEX_PYRAMID_SAND_SSL' : 'ssl_pyramid_sand', 'TEX_YELLOW_TRI_TTC' : 'ttc_yellow_triangle' }

    def __init__( self, coloured, movtex_args ):
        self.coloured = coloured
        self.geoid = None
        self.texture = None
        self.vert_count = None
        self.vtx_name = None
        self.begin_dl = None
        self.end_dl = None
        self.tri_dl = None
        self.static_colours = None
        self.colours = []
        self.layer = None
        self.speed = None
        self.positions = []
        self.triangles = []
        self.texel_coords = []
        self.render_settings = None
        self.drawlist = None
        self.parse_movtex_args( movtex_args )


    def copy( self ):
        for i in self.movtex_texture_dict:
            if self.movtex_texture_dict[ i ] == self.texture:
                copy_texture = i
        copy_static_colours = self.static_colours.copy()
        copy_object = Movtex_Tri( self.coloured, [ self.geoid, copy_texture, self.vert_count, self.vtx_name, self.begin_dl, self.end_dl, self.tri_dl, *copy_static_colours, self.layer ] )
        copy_object.colours = self.colours.copy()
        copy_object.speed = self.speed
        copy_object.positions = self.positions.copy()
        copy_object.triangles = self.triangles.copy()
        copy_object.texel_coords = self.texel_coords.copy()
        copy_object.render_settings = self.render_settings.copy()
        copy_object.drawlist = self.drawlist.copy()
        return copy_object


    def parse_movtex_args( self, movtex_args ):
        self.geoid = movtex_args[ 0 ]
        self.texture = self.movtex_texture_dict[ movtex_args[ 1 ] ]
        self.vert_count = movtex_args [ 2 ]
        self.vtx_name = movtex_args [ 3 ]
        self.begin_dl = movtex_args [ 4 ]
        self.end_dl = movtex_args[ 5 ]
        self.tri_dl = movtex_args[ 6 ]
        self.static_colours = movtex_args[ 7 : 11 ]
        if self.coloured == False:
            self.colours = self.static_colours * self.vert_count
        self.layer = movtex_args[ 11 ]


    def parse_tris( self, struct ):
        triangle_calls = struct.splitlines()
        for each_line in triangle_calls:
            if '2Triangles' in each_line:
                triangle_args = process_line( each_line )
                self.triangles += triangle_args[ 0 : 3 ]
                self.triangles += triangle_args[ 4 : 7 ]
            elif '1Triangle' in each_line:
                triangle_args = process_line( each_line )
                self.triangles += triangle_args[ 0 : 3 ]
        

    def parse_vtx( self, struct ):
        vertex_defs = struct.splitlines()
        current_vert_index = 0
        for each_line in vertex_defs:
            if 'MOV_TEX_SPD' in each_line:
                self.speed = process_line( each_line )
            if 'MOV_TEX_TRIS' in each_line:
                vert_args = process_line( each_line )
                self.positions += vert_args[ : 3 ]
                s_coord = vert_args[ 3 ]
                t_coord = vert_args[ 4 ]
                self.add_texel_coords( s_coord, t_coord, current_vert_index )
                current_vert_index += 1
            elif 'MOV_TEX_ROT_TRIS' in each_line:
                vert_args = process_line( each_line )
                self.positions += vert_args[ : 3 ]
                self.colours += [ convert_to_twos_complement( vert_args[ 3 ], 8 ), convert_to_twos_complement( vert_args[ 4 ], 8 ), convert_to_twos_complement( vert_args[ 5 ], 8 ), self.static_colours[ 3 ] ]
                s_coord = vert_args[ 6 ]
                t_coord = vert_args[ 7 ]
                self.add_texel_coords( s_coord, t_coord, current_vert_index )
                current_vert_index += 1
            elif 'MOV_TEX_LIGHT_TRIS' in each_line:
                vert_args = process_line( each_line )
                self.positions += vert_args[ : 3 ]
                y_normal = vert_args[ 3 ]
                self.colours += [ convert_to_twos_complement( 0, 8 ), convert_to_twos_complement( y_normal, 8 ), convert_to_twos_complement( 0, 8 ), self.static_colours[ 3 ] ]
                s_coord = vert_args[ 4 ]
                t_coord = vert_args[ 5 ]
                self.add_texel_coords( s_coord, t_coord, current_vert_index )
                current_vert_index += 1

        assert current_vert_index == self.vert_count, "An incorrect number of vertices were processed."
        assert len( self.positions ) // 3 == self.vert_count, "Wrong number of positions."
        assert len( self.texel_coords ) // 2 == self.vert_count, "Wrong number of texel_coords."
        assert len( self.colours ) // 4 == self.vert_count, "Wrong number of colours."


    def add_texel_coords( self, s, t, ind ):
        if ind == 0:
            self.texel_coords += [ s, t ]

        else:
            base_s = self.texel_coords[ 0 ]
            base_t = self.texel_coords[ 1 ]
            self.texel_coords += [ base_s + 1024 * s, base_t + 1024 * t ]


    def make_drawlist( self ):
        self.render_settings.current_texture = self.texture
        self.drawlist = GfxDrawList( self.geoid, self.render_settings, self.triangles, self.positions, self.texel_coords, self.colours )



def parse_movtex_struct( source ):
    struct_start = source.find( '\n', source.find( '=' ) ) + 1
    struct_end = source.rfind( '\n' ) - 1
    movtex_list = [ each_movtex.strip() for each_movtex in source[ struct_start : struct_end ].split( '},' ) ]
    ret_list = []
    for each_movtex in movtex_list:
        each_movtex = each_movtex.replace( '{', '(' )
        if '}' in each_movtex:
            each_movtex.replace( '}', ')' )
        else:
            each_movtex += ')'

        each_movtex_args = process_line( each_movtex )
        ret_list.append( each_movtex_args )

    return ret_list


def is_null_movtex( movtex ):
    return movtex == [0, 0, 0, 'NULL', 'NULL', 'NULL', 'NULL', 0, 0, 0, 0, 0]


def build_movtex_dict( mov_source ):
    structs = mov_source.split( ';' )
    
    movtex_dict = {}
    
    for each_struct in structs:
        if 'MovtexObject gMovtexNonColored' in each_struct:
            noncolored_movtexs = parse_movtex_struct( each_struct )
            for each_noncolored_movtex in noncolored_movtexs:
                if not is_null_movtex( each_noncolored_movtex ):
                    movtex_dict[ each_noncolored_movtex[ 0 ] ] = Movtex_Tri( False, each_noncolored_movtex )
                    
    
        elif 'MovtexObject gMovtexColored' in each_struct:
            colored_movtexs = parse_movtex_struct( each_struct )
            for each_colored_movtex in colored_movtexs:
                if not is_null_movtex( each_colored_movtex ):
                    movtex_dict[ each_colored_movtex[ 0 ] ] = Movtex_Tri( True, each_colored_movtex )

    return movtex_dict


def main( mario_source_dir, mario_graphics_dir ):

    filepath = mario_source_dir / 'src' / 'game' / 'moving_texture.c'
    
    mov_source = ''
    with open( filepath, 'r' ) as f:
        for line in f:
            if line.strip()[ : 2 ] != '//':
                mov_source += line
    
    
    movtex_dict = build_movtex_dict( mov_source )
    
    ## Now that we have the dictionary of movtexs, we need to open each movtex.inc.c file and find the corresponding vtx_name and tri_dl structs and parse those out.  We also need to keep track of render settings for begin_dl.  We can ignore end_dl.
    
    movtex_paths = [ each_path for each_path in mario_source_dir.glob( '**/movtext.inc.c' ) ]
    ## Of course they split things up into other non-movtext files.
    movtex_paths += [ mario_source_dir / 'levels' / 'ssl' / 'areas' / '2' / '4' / 'model.inc.c' ]
    ## Of course they have one Gfx randomly in a totally different file.
    movtex_paths += [ mario_source_dir / 'bin' / 'segment2.c' ]
    
    render_settings_dict = {}
    gfx_source_dict = {}
    
    for each_path in movtex_paths:
        with open( each_path, 'r' ) as f:
            movtext_source = f.read()
    
        structs = movtext_source.split( ';' )
    
        for each_struct in structs:
            name = get_movtex_name( each_struct )
            for each_movtex in movtex_dict.values():
                if name == each_movtex.tri_dl:
                    each_movtex.parse_tris( each_struct )
                elif name == each_movtex.vtx_name:
                    each_movtex.parse_vtx( each_struct )
                if name == each_movtex.begin_dl:
                    if gfx_source_dict.get( name ):
                        pass
                    else:
                        gfx_source_dict[ name ] = [ each_line for each_line in each_struct.split( '\n' ) ]
    
    
    with open( mario_graphics_dir / 'draw_dicts.pickle', 'rb' ) as f:
        vtx_dict, gfx_dict, light_dict, gfx_display_dict = pickle.load( f )
    
    ## We finally have everything in place to get render settings.
    for each_dl_name in gfx_source_dict:
        current_gfx = Gfx( each_dl_name, gfx_source_dict, vtx_dict, light_dict )
        render_settings_dict[ each_dl_name ] = current_gfx.render_settings
    
    ## Add render settings to each movtex and generate a drawlist.
    for each_movtex in movtex_dict.values():
        each_movtex.render_settings = render_settings_dict[ each_movtex.begin_dl ].copy()
        each_movtex.make_drawlist()
    
    
    
    """
    ## Sanity check.
    for each_movtex in movtex_dict.values():
        print( 'geoid =', each_movtex.geoid )
        print( 'coloured =', each_movtex.coloured )
        print( 'texture =', each_movtex.texture )
        print( 'vert_count =', each_movtex.vert_count )
        print( 'vtx_name =', each_movtex.vtx_name )
        print( 'begin_dl =', each_movtex.begin_dl )
        print( 'end_dl =', each_movtex.end_dl )
        print( 'tri_dl =', each_movtex.tri_dl )
        print( 'static_colours =', each_movtex.static_colours )
        print( 'layer =', each_movtex.layer )
        print( 'positions =', each_movtex.positions )
        print( 'triangles =', each_movtex.triangles )
        print( 'colours =', each_movtex.colours )
        print( 'texel_coords =', each_movtex.texel_coords )
        print( '\n' )
    """
    
    
    ## Now all we have to do is get render_settings for each begin_dl.  Once we have that, we can build a GfxDrawList.
    """
    temp_set = set()
    for each_movtex in movtex_dict.values():
        temp_set.add( each_movtex.begin_dl )
    print( temp_set )
    """
    ## There are only 8 required begin_dls.
    
    with open( mario_graphics_dir / 'movtex_dict.pickle', 'wb' ) as f:
        pickle.dump( movtex_dict, f, pickle.HIGHEST_PROTOCOL )
    
    print( "Saved movtex_dict to file." )



if __name__ == "__main__":
    mario_source_dir = Path( '/home/seph/mario_source/sm64/' )
    mario_graphics_dir = Path( '/home/seph/game_practice/mario_64_graphics/' )
    main( mario_source_dir, mario_graphics_dir )

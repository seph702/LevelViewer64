import pickle
from pathlib import Path

from .level_script_parser import process_line


def make_model_dict( mario_source_dir ):
    with open( mario_source_dir / 'include/model_ids.h' ) as f:
        txt = f.read()
    
    txt = txt[ txt.index( '#define MODEL_BOB_BUBBLY_TREE' ) : ]
    txt = txt.split( '\n' )
    model_dict = {}
    
    
    for each_line in txt:
        if each_line[ : 7 ] == '#define':
            temp_line = each_line.split( )
            if len( temp_line ) > 3:
                for i in range( len( temp_line ) ):
                    if temp_line[ i ] == '//':
                        ## hardcode to fix error in file
                        if temp_line[ 1 ] == 'MODEL_CHAIN_CHOMP':
                            model_dict[ temp_line[ 1 ] ] = 'chain_chomp_geo'
                        else:
                            model_dict[ temp_line[ 1 ] ] = temp_line[ i + 1 ]


    return model_dict


def make_macro_and_macro_to_geo_dicts( mario_source_dir ):
    macro_models = []

    with open( mario_source_dir / 'include/macro_presets.h' ) as f:
        txt = f.read()
    
    find_str = 'struct MacroPreset MacroObjectPresets[] = {'
    
    start_ind = txt.index( find_str ) + len( find_str )
    end_ind = txt.rindex( '};' )
    
    txt = txt[ start_ind : end_ind ]
    
    txt = txt.split( '{' )
    
    for each_line in txt:
        temp = each_line.split( ',' )
        if len( temp ) > 1:
            macro_models.append( temp[ 1 ].strip() )
    
    
    macro_names = []
    
    with open( mario_source_dir / 'include/macro_preset_names.h' ) as f:
        txt = f.read()
    
    l_index = txt.index( '{' ) + 1
    r_index = txt.index( '}' )
    
    txt = txt[ l_index : r_index ]
    
    macro_names = [ i.strip() for i in txt.split( ',\n' ) ]
    
    macro_dict = {}
    
    for i in range( len( macro_models ) ):
        macro_dict[ macro_names[ i ] ] = macro_models[ i ]
    
    
    ## composition dictionary that goes directly from macro_names to geo names:
    macro_to_geo_dict = {}
    
    for i in macro_dict:
        try:
            macro_to_geo_dict[ i ] = model_dict[ macro_dict[ i ] ]
        except:
            pass


    return macro_dict, macro_to_geo_dict



def make_special_dict( mario_source_dir ):

    with open( mario_source_dir / 'include/special_preset_names.h', 'r' ) as f:
        txt = f.read()
    
    
    start_ind = txt.index( '{' ) + 1
    end_ind = txt.rindex( '}' )
    
    txt = txt[ start_ind : end_ind ]
    txt = [ i.strip() for i in txt.split( ',' ) ]
    
    special_presets = [ None for i in range( 256 ) ]
    
    i_txt = 0
    i_special_presets = 0
    while i_special_presets < len( special_presets ):
        if '=' in txt[ i_txt ]:
            temp = [ j.strip() for j in txt[ i_txt ].split( '=' ) ]
            try:
                i_special_presets = int( temp[ -1 ], 16 )
                special_presets[ i_special_presets ] = temp[ 0 ]
            except:
                special_presets[ i_special_presets ] = temp[ 0 ]
    
        else:
            special_presets[ i_special_presets ] = txt[ i_txt ]
    
        i_txt += 1
        i_special_presets += 1
    
    
    with open( mario_source_dir / 'include/special_presets.h', 'r' ) as f:
        txt = f.read()
    
    find_str = 'static struct SpecialPreset SpecialObjectPresets[] ='
    start_ind = txt.index( '{', txt.index( find_str ) ) + 1
    end_ind = txt.index( '};', start_ind )
    
    txt = txt[ start_ind : end_ind ]
    txt = txt.replace( '{', '' )
    txt = txt.split( '},' )
    
    special_dict = {}
    for each_line in txt:
        temp = [ i.strip() for i in each_line.split( ',' ) ]
        special_dict[ special_presets[ int( temp[ 0 ], 16 ) ] ] = temp[ 3 ]

    return special_dict


#########################################
#########################################
#########################################

## Now, to translate special names in collision.inc.c files to model names, we call model_dict[ special_dict[ special_name_from_collision_file ] ]

def main( mario_source_dir, mario_graphics_dir ):
    model_dict = make_model_dict( mario_source_dir )
    macro_dict, macro_to_geo_dict = make_macro_and_macro_to_geo_dicts( mario_source_dir )
    special_dict = make_special_dict( mario_source_dir )

    ## Write dicts to file.
    with open( mario_graphics_dir / 'model_dicts.pickle' , 'wb' ) as f:
        pickle.dump( [ model_dict, macro_dict, macro_to_geo_dict, special_dict ], f, pickle.HIGHEST_PROTOCOL )
    
    print( "Model dictionaries written to file." )


if __name__ == "__main__":
    mario_source_dir = Path( '/home/seph/mario_source/sm64/' )
    mario_graphics_dir = Path( '/home/seph/game_practice/mario_64_graphics/' )
    main( mario_source_dir, mario_graphics_dir )

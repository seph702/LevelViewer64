from pathlib import Path
import pickle

def make_skybox_and_name_dictionaries( mario_source_dir ):

    levels_dir = mario_source_dir / 'levels'
    
    yaml_files = []
    skybox_filenames = [ mario_source_dir / 'textures' / 'skyboxes' / 'bidw.png',
    mario_source_dir / 'textures' / 'skyboxes' / 'wdw.png',
    mario_source_dir / 'textures' / 'skyboxes' / 'ccm.png',
    mario_source_dir / 'textures' / 'skyboxes' / 'bits.png',
    mario_source_dir / 'textures' / 'skyboxes' / 'bitfs.png',
    mario_source_dir / 'textures' / 'skyboxes' / 'bbh.png',
    mario_source_dir / 'textures' / 'skyboxes' / 'ssl.png',
    mario_source_dir / 'textures' / 'skyboxes' / 'clouds.png',
    mario_source_dir / 'textures' / 'skyboxes' / 'cloud_floor.png',
    mario_source_dir / 'textures' / 'skyboxes' / 'water.png', ]
    
    skybox_dict = {}
    name_dict = {}
    
    ## Process level.yaml first to get level names and skybox names.
    for f in levels_dir.glob( "**/*.yaml" ):
        yaml_files.append( f )
    
    
    short_names = []
    full_names = []
    level_textures = []
    skybox_bins = []
    for each_file in yaml_files:
        with open( each_file, 'r' ) as f:
            yaml = f.read()
    
        short_name_ind = yaml.find( 'short-name:' ) + 1
        end_name = yaml.find( '\n', short_name_ind + len( 'short-name:' ) )
        short_name = yaml[ short_name_ind + len( 'short-name:' ) : end_name ]
        short_names.append( short_name )
    
        full_name_ind = yaml.find( 'full-name:' ) + 1
        end_name = yaml.find( '\n', full_name_ind + len( 'full-name:' ) )
        full_name = yaml[ full_name_ind + len( 'full-name:' ) : end_name ]
        full_names.append( full_name )
        name_dict[ short_name ] = full_name
    
        level_textures_name_ind = yaml.find( '["/', yaml.find( 'texture-file:' ) + 1 ) + len( '["/' )
        end_name = yaml.find( ']', level_textures_name_ind + len( 'texture-file:' ) )
        level_textures_arr = yaml[ level_textures_name_ind : end_name ].split( ',' )
        for each_inc in level_textures_arr:
            level_textures.append( ( each_file.parent / each_inc.strip( '"' ) ) )
    
        skybox_name_ind = yaml.find( 'skybox-bin' ) + 1
        end_name = yaml.find( '\n', skybox_name_ind + len( 'skybox-bin' ) )
        level_skybox = yaml[ skybox_name_ind + len( 'skybox-bin:' ) : end_name ]
        skybox_bins.append( level_skybox )
        if level_skybox != 'null':
            skybox_dict[ short_name ] = level_skybox
        else:
            skybox_dict[ short_name ] = None

    return name_dict, skybox_dict


def make_texture_dictionary( mario_source_dir ):

    ## Next process texture includes
    texture_dict = {}
    
    bin_files = []
    for f in mario_source_dir.glob( "**/*.c" ):
        bin_files.append( f )
    
    tot_textures = 0
    textures_found = 0
    found_textures = []
    
    for each_file in bin_files:
        with open( each_file, 'r' ) as f:
            try:
                source = f.read()
            except:
                continue
    
        match_str1 = 'ALIGNED8 const u8 '
        match_str2 = 'ALIGNED8 static const u8 '
        match_str3 = 'ALIGNED8 static u8 '
        m1_len = len( match_str1 )
        m2_len = len( match_str2 )
        m3_len = len( match_str3 )
    
        i = 0
        while i < len( source ):
            
            check1 = source[ i : i + m1_len ] == match_str1
            check2 = source[ i : i + m2_len ] == match_str2
            check3 = source[ i : i + m3_len ] == match_str3
    
            if check1 or check2 or check3:
                end_name = source.find( '[', i )
                if check1:
                    texture_name = source[ i + m1_len : end_name ]
    
                if check2:
                    texture_name = source[ i + m2_len : end_name ]
    
                if check3:
                    texture_name = source[ i + m3_len : end_name ]
    
                start_texture_file = source.find( '"', end_name ) + 1
                end_texture_file = source.find( '"', start_texture_file + 1 )
                texture_filename = source[ start_texture_file : end_texture_file ]
                texture_filename_png = texture_filename[ : -5 ] + 'png'
                ## Test texture_filename_png to make sure we have it:
                try:
                    with open( mario_source_dir / texture_filename_png, 'rb' ) as g:
                        g.read()
                        textures_found += 1
                        found_textures.append( str( ( mario_source_dir / texture_filename_png ).resolve() ) )
                        texture_dict[ texture_name ] = str( ( mario_source_dir / texture_filename_png ).resolve() )
                except:
                    pass
                    #print( 'Missing', texture_name, texture_filename_png )
    
                tot_textures += 1
    
    
            i += 1
    
    
    folders = [ str( ( mario_source_dir / 'textures' ).resolve() ) ]
    for f in ( mario_source_dir / 'textures' ).glob( '*' ):
        folders.append( str( f.resolve() ) )
    
    t_list = []
    for f in ( mario_source_dir / 'textures' ).glob( '**' ):
        if 'skyboxes' not in str( f.resolve() ) and str( f.resolve() ) not in folders:
            t_list.append( f )
    
    missing_count = 0
    for i in t_list:
        if i not in found_textures:
            print( "Missing texture:", i )
            missing_count += 1
    
    #print( tot_textures, "total textures." )
    print( textures_found + missing_count, "total expected textures." )
    print( textures_found, "textures found." )
    print( missing_count, "total missing textures." )

    return texture_dict


def main( mario_source_dir, mario_graphics_dir ):

    texture_dict = make_texture_dictionary ( mario_source_dir )
    name_dict, skybox_dict = make_skybox_and_name_dictionaries( mario_source_dir )

    with open( mario_graphics_dir / 'm64_dicts.pickle', 'wb' ) as f:
        pickle.dump( [ skybox_dict, texture_dict, name_dict ], f, pickle.HIGHEST_PROTOCOL )
    
    print( "Skybox and texture dictionaries written to file." )


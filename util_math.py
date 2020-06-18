import numpy as np
import zlib
import struct


################################
### 3D MATH MATRIX FUNCTIONS ###
################################

def normalize( arr, axis=-1, order=2 ):
    l2 = np.atleast_1d( np.linalg.norm( arr, order, axis ) )
    l2[ l2==0 ] = 1
    return arr / np.expand_dims( l2, axis )


def identity_mat():
    return np.eye( 4 )


def scale_mat( scale ):
    return np.array( [ [ scale,   0.0, 0.0, 0.0 ],
                        [ 0.0, scale,   0.0, 0.0 ],
                        [ 0.0, 0.0, scale,   0.0 ],
                        [ 0.0, 0.0, 0.0, 1.0 ] ] )


def translate_mat( x=0.0, y=0.0, z=0.0 ):
    return np.array( [ [ 1.0, 0.0, 0.0, 0.0 ],
                        [ 0.0, 1.0, 0.0, 0.0 ],
                        [ 0.0, 0.0, 1.0, 0.0 ],
                        [  x,   y,   z,  1.0 ] ] )


def rotate_around_x( angle ):
    rads = np.radians( angle )
    c = np.cos( rads )
    s = np.sin( rads )
    return np.array( [ [ 1.0, 0.0, 0.0, 0.0 ],
                        [ 0.0,  c ,  s , 0.0 ],
                        [ 0.0,  -s,  c , 0.0 ],
                        [ 0.0, 0.0, 0.0, 1.0 ] ] )


def rotate_around_y( angle ):
    rads = np.radians( angle )
    c = np.cos( rads )
    s = np.sin( rads )
    return np.array( [ [  c , 0.0, -s , 0.0 ],
                        [ 0.0, 1.0, 0.0, 0.0 ],
                        [  s , 0.0,  c,  0.0 ],
                        [ 0.0, 0.0, 0.0, 1.0 ] ] )


def rotate_around_z( angle ):
    rads = np.radians( angle )
    c = np.cos( rads )
    s = np.sin( rads )
    return np.array( [ [  c ,  s , 0.0, 0.0 ],
                        [  -s,  c , 0.0, 0.0 ],
                        [ 0.0, 0.0, 1.0, 0.0 ],
                        [ 0.0, 0.0, 0.0, 1.0 ] ] )


def rotate_around_vec( angle, x, y, z ):
    rads = np.radians( angle )
    c = np.cos( rads )
    s = np.sin( rads )
    m = 1 - c
    return np.array( [ x**2 * m + c, x * y * m + z * s, x * z * m - y * s, 0 ],
                      [ x * y * m - z * s, y**2 * m + c, y * z * m + x * s, 0 ],
                      [ x * z * m + y * s, y * z * m - x * s, z**2 * m + c, 0 ],
                      [        0,                 0,              0,        1 ] )

def positions_to_mat( positions ):
    ret_mat = np.ones( ( len( positions ) // 3, 4 ) )
    ret_mat[ :, : -1 ] = np.array( positions ).reshape( ( -1, 3 ) )
    return ret_mat

def normals_to_mat( normals ):
    ret_mat = np.zeros( ( len( normals ) // 3, 4 ) )
    ret_mat[ :, : -1 ] = np.array( normals ).reshape( ( -1, 3 ) )
    return ret_mat


def mat_to_positions( mat ):
    """
    Assumes mat is of shape ( -1, 4 ) and converts it to a python list such that values are x1, y1, z1, x2, y2, z2, x3, ...
    """
    return mat[ :, : -1 ].ravel().tolist()


#####################################
### N64 TYPE CONVERSION FUNCTIONS ###
#####################################


def s10_5_to_int( a ):
    """Converts a number in S10.5 format ( sign bit, 10 bits for whole number, 5 bits for fractional part ) to float."""
    integer_part = a >> 5
    fractional_as_int = a & 31
    fractional_part = fractional_as_int / 32
    return integer_part + fractional_part

def twos_comp( val, bits ):
    """Converts unsigned value representing a signed value using two's complement into the proper range given bits."""
    if ( val & ( 1 << ( bits - 1 ) ) ) != 0 :
        val = val - ( 1 << bits )
    return val

def convert_twos_comp_list( arr ):
    """
    Takes in a list of byte values ( 0 - 255 ), converts them to their two's complement value, and then normalizes to -1 to 1 by dividing by 127 ( if positive ) or 128 ( if negative ).
    """
    ret_list = []
    for each_val in arr:
        signed_val = twos_comp( each_val, 8 )
        if signed_val < 0:
            ret_list.append( signed_val / 128.0 )
        else:
            ret_list.append( signed_val / 127.0 )

    return ret_list


##########################
### PNG WRITE FUNCTION ###
##########################

## Thanks, ideasman42!  ( https://stackoverflow.com/a/19174800/981933 )

def png_pack( png_tag, data ):
    chunk_head = png_tag + data
    return ( struct.pack( "!I", len( data ) ) +
            chunk_head +
            struct.pack( "!I", 0xFFFFFFFF & zlib.crc32( chunk_head ) ) )


def write_png( buf, width, height ):
    """ buf: must be bytes or a bytearray in Python3.x,
        a regular string in Python2.x.
    """
    # Reverse the vertical line order and add null bytes at the start.
    width_byte_4 = width * 4
    raw_data = b''.join(
        b'\x00' + buf[ span : span + width_byte_4 ]
        for span in range( ( height - 1 ) * width_byte_4, -1, - width_byte_4 )
    )

    return b''.join( [
        b'\x89PNG\r\n\x1a\n',
        png_pack( b'IHDR', struct.pack( "!2I5B", width, height, 8, 6, 0, 0, 0 ) ),
        png_pack( b'IDAT', zlib.compress( raw_data, 9 ) ),
        png_pack( b'IEND', b'' ) ] )

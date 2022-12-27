import socket
import json

def send_msg( dst, msg ):
    length = len(msg).to_bytes( 4, 'big' )# 4-byte integer, network byte order (Big Endian)
    dst.send( length )
    dst.send( msg )

def exact_recv( src, length ):
    data = bytearray( 0 )

    while len(data) != length:
        more_data = src.recv( length - len(data) )
        if len(more_data) == 0: # End-of-File
            return None
        data.extend( more_data )

    if data == None:  # Socket closed
        # Gerar uma Classe de Erro (CDProtoBadFormat)
        return None

    return data

def recv_msg( src ):
    data = exact_recv( src, 4 ) # 4-byte integer, network byte order (Big Endian)
    if data == None:
        return None

    length = int.from_bytes( data, 'big' )
    data =  exact_recv( src, length )
    return json.loads(data.decode('UTF-8'))
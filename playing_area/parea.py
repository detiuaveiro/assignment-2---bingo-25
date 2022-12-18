#!/bin/python

import sys
import socket
import selectors
import json
import messages as m

def dispatch( srv_socket ):
    selector = selectors.DefaultSelector()

    srv_socket.setblocking( False )
    selector.register( srv_socket, selectors.EVENT_READ, data=None )

    while True:
        print( 'Select' )
        events = selector.select( timeout=None )
        for key, mask in events:

            # Check for a new client connection

            if key.fileobj == srv_socket:
                clt_socket, clt_addr = srv_socket.accept()
                clt_socket.setblocking( True )

                # Add it to the sockets under scrutiny

                selector.register( clt_socket, selectors.EVENT_READ, data=None )
                print( 'Client added' )

            # Client data is available for reading

            else:
                data = m.recv_msg( key.fileobj )

                if data == None: # Socket closed
                    selector.unregister( key.fileobj )
                    key.fileobj.close()
                    print( 'Client removed' )
                    continue

                data = json.loads( data.decode( 'UTF-8' ) )
                print( data )

                data['body']  = data['body'].upper()
                data = json.dumps( data )
                data = data.encode( 'UTF-8' )
                m.send_msg( key.fileobj, data )

def main():
    if len(sys.argv) != 2:
        print( 'Usage: %s port' % (sys.argv[0]) )
        sys.exit( 1 )

    with socket.socket( socket.AF_INET, socket.SOCK_STREAM ) as s:
        s.bind( ('0.0.0.0', int(sys.argv[1]) ) )
        s.listen()
        dispatch( s )

if __name__ == '__main__':
    main()
#!/bin/python

import sys
import socket
import json
import messages as m

def main():
    if len(sys.argv) != 2:
        print( 'Usage: %s port' % (sys.argv[0]) )
        sys.exit( 1 )

    message = { 'header': 'something', 'body': '' }

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect( ( '127.0.0.1', int(sys.argv[1]) ) )
        for line in sys.stdin:
            message['body'] = line
            m.send_msg( s, json.dumps( message ).encode( 'UTF-8' ) )

            data = m.recv_msg( s )
            if data == None:
                 break

            data = json.loads( data.decode( 'UTF-8' ) )
            print( data )

if __name__ == '__main__':
    main()
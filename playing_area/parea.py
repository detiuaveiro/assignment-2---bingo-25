#!/bin/python

import sys
import socket
import selectors
import json
from messages import send_msg, exact_recv, recv_msg

CONNECTED_CLIENTS = {}                              # Dictionary holding the Connected Clients {ID: socket}
CURRENT_ID = 1

def dispatch( srv_socket ):
    selector = selectors.DefaultSelector()
    global CURRENT_ID

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
                msg = recv_msg( key.fileobj )

                if msg == None:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    print('Client removed')
                    continue

                read_data(msg, key.fileobj)

def read_data(msg, socket):
    """
    This function will determine the class of the received Message, and call the code that should be executed when an instance of this Message is received.
    :param msg: The message received
    :param socket: The socket that sent the message
    :return:
    """

    '''
    CÓDIGO A SER USADO APÓIS IMPLEMENTAÇÃO DO PROTOCOLO DE MENSAGENS
        if isinstance(msg, ProtoBadFormat): # Socket closed
            selector.unregister( key.fileobj )
            key.fileobj.close()
            print( 'Client removed' )
            continue
        elif isinstance(msg, RegisterMessage):
            pass 
    '''

    ''' CÓDIGO USADO PARA TESTE ENQUANTO PROTOCOLO DE MENSAGENS NÃO FOR IMPLEMENTADO '''
    reply = None
    print(msg)

    if msg['class'] == "Register":
        # REGISTER MESSAGE
        reply = register_new_client(msg, socket)


    if reply != None:
        reply = json.dumps(reply)
        reply = reply.encode('UTF-8')
        send_msg(socket, reply)


def register_new_client(msg, socket):
    """
    Function that will verify a Register Message to check whether the new Client can be registered as a Player/Caller or not.
    :param msg:
    :param socket:
    :return:
    """
    reply = None

    if msg['type'] == "Caller":
        if 0 in CONNECTED_CLIENTS.keys():
            # We already have a Caller registered in the Playing Area
            reply = {'class': "Register NACK"}
        else:
            CONNECTED_CLIENTS[0] = socket
            reply = {'class': "Register ACK"}
    else:
        CONNECTED_CLIENTS[CURRENT_ID] = socket
        CURRENT_ID += 1
        reply = {'class': "Register ACK"}

    return reply


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
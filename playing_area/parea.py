#!/bin/python

import sys
import socket
import selectors
import json
from time import sleep
from pathlib import Path

path_root = Path(__file__).parents[1]
sys.path.append(str(path_root))

from messages.messages import send_msg, recv_msg

CONNECTED_PLAYERS = {}                              # Dictionary holding the Connected Clients {ID: socket}
CALLER = {}
CURRENT_ID = 1
NUMBER_OF_PLAYERS = 4

def dispatch( srv_socket ):
    selector = selectors.DefaultSelector()

    srv_socket.setblocking( False )
    selector.register( srv_socket, selectors.EVENT_READ, data=None )

    while True:
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
                    if key.fileobj in CALLER.values():
                        CALLER.pop(0)
                        print( 'Caller removed' )
                    else:
                        key_to_remove = next((k for k, value in CONNECTED_PLAYERS.items() if value == key.fileobj), None)
                        if key_to_remove != None:
                            CONNECTED_PLAYERS.pop(key_to_remove)
                            print( 'Client removed' )
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
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
    CÓDIGO A SER USADO APÓS IMPLEMENTAÇÃO DO PROTOCOLO DE MENSAGENS
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
    elif msg['class'] == "BEGIN_GAME":
        # Fazer forward da Mensagem para todos os jogadores
        broadcast_to_players(msg)


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
    global NUMBER_OF_PLAYERS
    global CURRENT_ID

    if msg['type'] == "Caller":
        if len(CALLER.keys()) > 0:
            # We already have a Caller registered in the Playing Area
            reply = {'class': "Register NACK"}
        else:
            CALLER[0] = socket
            reply = {'class': "Register ACK"}
            NUMBER_OF_PLAYERS = msg['number_of_players']
    else:
        # User do tipo Cliente
        if len(CONNECTED_PLAYERS.keys()) > NUMBER_OF_PLAYERS or len(CALLER.keys()) == 0:
            # Recusar ligação de novo Player
            reply = {'class': "Register NACK"}
        else:
            CONNECTED_PLAYERS[CURRENT_ID] = socket
            CURRENT_ID += 1
            reply = {'class': "Register ACK"}

            # Redirect to the Caller player registration
            send_msg(CALLER[0], json.dumps(msg).encode('UTF-8'))

    return reply

def broadcast_to_players(msg):
    """
    Broadcasts a message to all Players
    :param msg:
    :return:
    """

    for player in CONNECTED_PLAYERS.keys():
        send_msg(CONNECTED_PLAYERS[player], msg)

def main():
    if len(sys.argv) != 3:
        print( 'Usage: %s port number_players' % (sys.argv[0]) )
        sys.exit( 1 )

    with socket.socket( socket.AF_INET, socket.SOCK_STREAM ) as s:
        s.bind( ('0.0.0.0', int(sys.argv[1]) ) )
        s.listen()
        dispatch( s )

if __name__ == '__main__':
    main()
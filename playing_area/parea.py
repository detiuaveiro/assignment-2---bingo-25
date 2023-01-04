#!/bin/python

import sys
import socket
import selectors
import click
from pathlib import Path

path_root = Path(__file__).parents[1]
sys.path.append(str(path_root))

import messages.protocol as proto

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
                print( 'Socket connection added' )

            # Client data is available for reading
            else:
                msg = proto.Protocol.recv_msg( key.fileobj )

                if msg == None:
                    if key.fileobj in CALLER.values():
                        CALLER.pop(0)
                        print( 'Caller removed' )
                        print( 'Shutting down, as the game now has no caller...')
                        exit()
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
    reply = None
    print(msg)

    if isinstance(msg, proto.RegisterMessage):
        # REGISTER MESSAGE
        reply = register_new_client(msg, socket)
    elif isinstance(msg, proto.Begin_Game):
        # Fazer forward da Mensagem para todos os jogadores
        broadcast_to_players(msg)

    if reply != None:
        proto.Protocol.send_msg(socket, reply)


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

    if msg.type == "Caller":
        if len(CALLER.keys()) > 0:
            # We already have a Caller registered in the Playing Area
            reply = proto.Register_NACK()
        else:
            CALLER[0] = socket
            NUMBER_OF_PLAYERS = msg.num_players
            reply = proto.Register_ACK()
    else:
        # User do tipo Cliente
        if len(CONNECTED_PLAYERS.keys()) > NUMBER_OF_PLAYERS or len(CALLER.keys()) == 0:
            # Recusar ligação de novo Player
            reply = proto.Register_NACK()
        else:
            CONNECTED_PLAYERS[CURRENT_ID] = socket
            CURRENT_ID += 1
            reply = proto.Register_ACK()

            # Redirect to the Caller player registration
            proto.Protocol.send_msg(CALLER[0], msg)

    return reply

def broadcast_to_players(msg):
    """
    Broadcasts a message to all Players
    :param msg:
    :return:
    """
    for player in CONNECTED_PLAYERS.keys():
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player], msg)

@click.command()
@click.option('--port', '-p', type=int, required=True, help='Port to connect to the Playing Area')
def main(port):
    with socket.socket( socket.AF_INET, socket.SOCK_STREAM ) as s:
        s.bind( ('0.0.0.0', port ) )
        s.listen()
        dispatch( s )

if __name__ == '__main__':
    main()
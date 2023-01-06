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
                            print( 'Player removed' )
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
        #TODO: Incluir na mensagem as chaves públicas de todos os jogadores
        print("The game will now start...")
        print("Step 1. Generation of the Playing Deck and the Player Cards")
        broadcast_to_players(msg)
    elif isinstance(msg, proto.Message_Deck):
        # Processo de shuffling do deck
        deck_generation(msg.deck)
    elif isinstance(msg, proto.Sign_Final_Deck_ACK):
        print("Step 2: Validating player cards")
        verify_playing_cards(msg.playing_cards)
    elif isinstance(msg, proto.Disqualify):
        broadcast_to_players(msg)
    elif isinstance(msg, proto.Cards_Validated):
        print("Step 3: Validating the Playing Deck")
        # Pedir chaves simétricas a todos os Utilizadors e enviar para o Caller
        reply = share_sym_keys()
    elif isinstance(msg, proto.Post_Final_Decks):
        print("Received all decks and symmetric keys. Broadcasting to players...")
        verify_playing_deck(msg)
    elif isinstance(msg, proto.Ask_For_Winner):
        print("Step 4: Determining the Winner")
        broadcast_to_players(msg)
    elif isinstance(msg, proto.Winner):
        proto.Protocol.send_msg(CALLER[0], msg)
    elif isinstance(msg, proto.Winner_ACK):
        broadcast_to_players(msg)
        print("The game as finished")
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
            reply = proto.Register_ACK(0)
    else:
        # User do tipo Cliente
        if len(CONNECTED_PLAYERS.keys()) > NUMBER_OF_PLAYERS or len(CALLER.keys()) == 0:
            # Recusar ligação de novo Player
            reply = proto.Register_NACK()
        else:
            CONNECTED_PLAYERS[CURRENT_ID] = socket
            reply = proto.Register_ACK(CURRENT_ID)
            CURRENT_ID += 1

            # Redirect to the Caller player registration
            proto.Protocol.send_msg(CALLER[0], msg)

    return reply

def deck_generation(initial_deck):
    """
    The Playing Area will redirect the initial deck created by the Caller to each Player, in turn, in order to shuffle the deck.
    During this process, the Playing Area will also receive the Playing Card form each Player
    :param initial_deck: The initial deck created by the Caller
    """
    print("Deck shuffling process beginning: ")
    current_deck = initial_deck

    for player in CONNECTED_PLAYERS.keys():
        # Enviar o deck ao jogador
        print(f"Sending deck to player {player}.")
        msg = proto.Message_Deck(current_deck)
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player], msg)

        # Esperar pela resposta
        reply = proto.Protocol.recv_msg(CONNECTED_PLAYERS[player])
        setattr(reply, 'id_user', player)

        proto.Protocol.send_msg(CALLER[0], reply)

        print("Sent deck to Caller.")

        if isinstance(reply, proto.Commit_Card):
            current_deck = reply.deck

    proto.Protocol.send_msg(CALLER[0], proto.Message_Deck(current_deck))


def verify_playing_cards(playing_cards):
    """
    The Playing Area will receive the Playing Cards from each Player, and will verify whether they are valid or not.
    :return:
    """
    verified_playing_cards = {user_id : True for user_id in CONNECTED_PLAYERS.keys()}
    print("Validating playing cards...")
    for player in CONNECTED_PLAYERS.keys():
        # Enviar a carta ao jogador
        print(f"Sending playing cards to player {player}.")
        msg = proto.Verify_Cards(playing_cards)
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player], msg)

        # Esperar pela resposta 
        reply = proto.Protocol.recv_msg(CONNECTED_PLAYERS[player])

        if isinstance(reply, proto.Verify_Card_NOK):
            for player in reply.users:
                print(f"Card from player {player} is invalid.")
                verified_playing_cards[player] = False
    
    # Enviar a resposta ao Caller
    proto.Protocol.send_msg(CALLER[0], proto.Cheat_Verify(verified_playing_cards, "Cards"))


def verify_playing_deck(msg):
    players_cheated = {user_id: True for user_id in CONNECTED_PLAYERS.keys()}
    print("Validating playing deck...")

    for player in CONNECTED_PLAYERS.keys():
        # Enviar a carta ao jogador
        print(f"Sending playing deck to player {player}.")
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player], msg)

        # Esperar pela resposta
        reply = proto.Protocol.recv_msg(CONNECTED_PLAYERS[player])

        if isinstance(reply, proto.Verify_Deck_NOK):
            for player in reply.users:
                print(f"Player {player} cheated!")
                players_cheated[player] = False

    # Enviar a resposta ao Caller
    proto.Protocol.send_msg(CALLER[0], proto.Cheat_Verify(players_cheated, "Deck"))

def share_sym_keys():
    sym_keys = {}

    # Pedir a chave simétrica a todos os Players
    msg = proto.Ask_Sym_Keys()

    for player in CONNECTED_PLAYERS.keys():
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player], msg)
        reply = proto.Protocol.recv_msg(CONNECTED_PLAYERS[player])

        print(reply)
        sym_keys[player] = reply.sym_key

    # Enviar chaves simétricas ao Caller
    return proto.Post_Sym_Keys(sym_keys)


def broadcast_to_players(msg):
    """
    Broadcasts a message to all Players
    :param msg:
    :return:
    """
    for player in CONNECTED_PLAYERS.keys():
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player], msg)


def broadcast_to_everyone(msg):
    """
    Broadcasts a message to all Users (Players + Caller)
    :param msg:
    :return:
    """
    for player in CONNECTED_PLAYERS.keys():
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player], msg)

    proto.Protocol.send_msg(CALLER[0], msg)

@click.command()
@click.option('--port', '-p', type=int, required=True, help='Port to connect to the Playing Area')
def main(port):
    with socket.socket( socket.AF_INET, socket.SOCK_STREAM ) as s:
        s.bind( ('0.0.0.0', port ) )
        s.listen()
        dispatch( s )

if __name__ == '__main__':
    main()
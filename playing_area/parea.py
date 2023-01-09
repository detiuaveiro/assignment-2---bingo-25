#!/bin/python

import sys
import socket
import selectors
from time import sleep
import click
from pathlib import Path
from cryptography.hazmat.primitives import serialization

path_root = Path(__file__).parents[1]
sys.path.append(str(path_root))

import messages.protocol as proto
import security.security as secure

CONNECTED_PLAYERS = {}                              # Dictionary holding the Connected Clients {ID: socket}
PLAYERS_INFO = {}
CALLER = {}
CURRENT_ID = 1
NUMBER_OF_PLAYERS = 4
PUBLIC_KEY = None
PRIVATE_KEY = None

def dispatch( srv_socket ):
    global PRIVATE_KEY
    global PUBLIC_KEY

    selector = selectors.DefaultSelector()

    srv_socket.setblocking( False )
    selector.register( srv_socket, selectors.EVENT_READ, data=None )

    # Generate assymetric key pair for signing Messages
    PRIVATE_KEY, PUBLIC_KEY = secure.gen_assymetric_key()

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
                msg, signature = proto.Protocol.recv_msg(key.fileobj)
                #print(f"Received message: {msg}")

                if signature is not None:
                    # Verify if the signature of the message belongs to the Client that sent it
                    sender_ID = msg.ID
                    if sender_ID == 0:
                        sender_pub_key = CALLER[sender_ID]["public_key"]
                    else:
                        sender_pub_key = CONNECTED_PLAYERS[sender_ID]["public_key"]

                    if not secure.verify_signature(msg, signature, sender_pub_key):
                        # If the Client signature is fake
                        if sender_ID == 0:
                            # The game is compromised, shut PA down
                            print('The Caller signature was forged! The game is compromised.')
                            print('Shutting down, as the game now has no caller...')
                            selector.unregister(key.fileobj)
                            key.fileobj.close()
                            exit()
                        else:
                            # Disqualify Player
                            m = proto.Disqualify(msg.ID)
                            signature = secure.sign_message(m, PRIVATE_KEY)
                            new_msg = proto.Message(m, signature)
                            proto.Protocol.send_msg(CALLER[0]["socket"], new_msg)
                            pass

                if msg == None:
                    if key.fileobj == CALLER[0]["socket"]:
                        CALLER.pop(0)
                        print( 'Caller removed' )
                        print( 'Shutting down, as the game now has no caller...')
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                        exit()
                    else:
                        key_to_remove = next((k for k, value in CONNECTED_PLAYERS.items() if value == key.fileobj), None)
                        if key_to_remove != None:
                            CONNECTED_PLAYERS.pop(key_to_remove)
                            print( 'Player removed' )
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue

                read_data(msg, signature, key.fileobj)

def read_data(msg, signature, socket):
    """
    This function will determine the class of the received Message, and call the code that should be executed when an instance of this Message is received.
    :param msg: The message received
    :param socket: The socket that sent the message
    :return:
    """
    global PRIVATE_KEY

    reply = None

    if isinstance(msg, proto.RegisterMessage):
        # REGISTER MESSAGE
        reply = register_new_client(msg, socket)
    elif isinstance(msg, proto.Begin_Game):
        # Fazer forward da Mensagem para todos os jogadores
        print("Registration process is completed!\n\nTHE GAME WILL NOW START")
        print("\nStep 1. Generation of the Playing Deck and the Player Cards")
        msg.ID = None
        signature = secure.sign_message(msg, PRIVATE_KEY)
        broadcast_to_players(msg, signature)
    elif isinstance(msg, proto.Message_Deck):
        # Processo de shuffling do deck
        deck_generation(msg.deck)
    elif isinstance(msg, proto.Sign_Final_Deck_ACK):
        print("\nStep 2: Validating player cards")
        reply = verify_playing_cards(msg.playing_cards)
    elif isinstance(msg, proto.Disqualify):
        broadcast_to_players(msg, signature)
        CONNECTED_PLAYERS.pop(int(msg.disqualified_ID))
        PLAYERS_INFO[int(msg.disqualified_ID)]["disqualified"] = True
    elif isinstance(msg, proto.Cards_Validated):
        print("\nStep 3: Validating the Playing Deck")
        # Pedir chaves simétricas a todos os Utilizadors e enviar para o Caller
        reply = share_sym_keys()
    elif isinstance(msg, proto.Post_Final_Decks):
        print("Received all decks and symmetric keys. Broadcasting to players...")
        reply = verify_playing_deck(msg, signature)
    elif isinstance(msg, proto.Ask_For_Winner):
        print("\nStep 4: Determining the Winner")
        broadcast_to_players(msg, signature)
    elif isinstance(msg, proto.Winner):
        proto.Protocol.send_msg(CALLER[0]["socket"], msg)
    elif isinstance(msg, proto.Winner_ACK):
        broadcast_to_players(msg, signature)
        print("\nThe game has succesfully finished!")
    elif isinstance(msg, proto.Get_Players_List):
        print("Received request for Players List")
        reply = proto.Players_List(None, PLAYERS_INFO)


    if reply != None:
        signature = secure.sign_message(reply, PRIVATE_KEY)
        reply = proto.SignedMessage(reply, signature)
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
    global PUBLIC_KEY

    if msg.type == "Caller":
        if len(CALLER.keys()) > 0:
            # We already have a Caller registered in the Playing Area
            reply = proto.Register_NACK()
        else:
            CALLER[0] = {"socket": socket, "public_key": msg.pk}
            NUMBER_OF_PLAYERS = msg.num_players
            reply = proto.Register_ACK(0, PUBLIC_KEY)
            print(f"{msg.nick} is now the Caller of the game.")
    else:
        # User do tipo Cliente
        if len(CONNECTED_PLAYERS.keys()) > NUMBER_OF_PLAYERS or len(CALLER.keys()) == 0:
            # Refuse new player connection
            reply = proto.Register_NACK()
        else:
            CONNECTED_PLAYERS[CURRENT_ID] = {"socket": socket, "public_key": msg.pk}
            PLAYERS_INFO[CURRENT_ID] = {"nick": msg.nick, "disqualified": False, "playing_card": None, "public_key": msg.pk}
            reply = proto.Register_ACK(CURRENT_ID, PUBLIC_KEY)
            CURRENT_ID += 1

            # Redirect to the Caller player registration signed
            signature = secure.sign_message(msg, PRIVATE_KEY)
            r = proto.SignedMessage(msg, signature)
            proto.Protocol.send_msg(CALLER[0]["socket"], r)

            print(f"Welcome to the Playing Area, {msg.nick}.")

    return reply

def deck_generation(initial_deck):
    """
    The Playing Area will redirect the initial deck created by the Caller to each Player, in turn, in order to shuffle the deck.
    During this process, the Playing Area will also receive the Playing Card form each Player
    :param initial_deck: The initial deck created by the Caller
    """
    global PRIVATE_KEY
    print("Deck shuffling process beginning: ")
    current_deck = initial_deck

    for player in CONNECTED_PLAYERS.keys():
        # Send the Deck to the Player
        print(f"Sending deck to player {player}.")
        msg = proto.Message_Deck(None, current_deck)
        singature = secure.sign_message(msg, PRIVATE_KEY)
        new_msg = proto.SignedMessage(msg, singature)
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player]["socket"], new_msg)

        # Wait for the reply
        while(True):
            reply, signature = proto.Protocol.recv_msg(CONNECTED_PLAYERS[player]["socket"])
            if isinstance(reply, proto.Commit_Card):
                # If the player is sending a CHEAT message, ignore, else continue the process
                break

        # Sign the reply with the private key of the PA
        proto.Protocol.send_msg(CALLER[0]["socket"], reply)

        print(f"Player {player} has returned their shuffled verson of the deck and their playing card. Forwarding the deck to the Caller.")

        if isinstance(reply, proto.Commit_Card):
            current_deck = reply.deck

    proto.Protocol.send_msg(CALLER[0]["socket"], proto.Message_Deck(None, current_deck))


def verify_playing_cards(playing_cards):
    """
    The Playing Area will receive the Playing Cards from each Player, and will verify whether they are valid or not.
    :return:
    """
    global PRIVATE_KEY

    verified_playing_cards = {user_id : True for user_id in CONNECTED_PLAYERS.keys()}

    msg = proto.Verify_Cards(None, playing_cards)
    signature = secure.sign_message(msg, PRIVATE_KEY)
    new_msg = proto.SignedMessage(msg, signature)

    for player in CONNECTED_PLAYERS.keys():
        # Enviar a carta ao jogador
        print(f"Sending all Playing Cards to player {player}, and waiting for their validation")
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player]["socket"], new_msg)

        # Esperar pela resposta 
        reply, signature = proto.Protocol.recv_msg(CONNECTED_PLAYERS[player]["socket"])

        if isinstance(reply, proto.Verify_Card_NOK):
            for player in reply.users:
                print(f"Card from player {player} is invalid.")
                verified_playing_cards[player] = False

        PLAYERS_INFO[player]["playing_card"] = playing_cards[str(player)]
    
    # Enviar a resposta ao Caller
    return proto.Cheat_Verify(verified_playing_cards, "Cards")


def verify_playing_deck(msg, signature):
    global PRIVATE_KEY
    players_cheated = {user_id: True for user_id in CONNECTED_PLAYERS.keys()}

    new_msg = proto.SignedMessage(msg, signature)

    for player in CONNECTED_PLAYERS.keys():
        # Enviar a carta ao jogador
        print(f"Sending playing deck to player {player}.")
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player]["socket"], new_msg)

        # Esperar pela resposta
        reply, signature = proto.Protocol.recv_msg(CONNECTED_PLAYERS[player]["socket"])

        if isinstance(reply, proto.Verify_Deck_NOK):
            for player in reply.users:
                print(f"Player {player} cheated!")
                players_cheated[player] = False

    # Enviar a resposta ao Caller
    return proto.Cheat_Verify(players_cheated, "Deck")

def share_sym_keys():
    global PRIVATE_KEY
    sym_keys = {}

    # Pedir a chave simétrica a todos os Players
    msg = proto.Ask_Sym_Keys()
    signature = secure.sign_message(msg, PRIVATE_KEY)
    new_msg = proto.SignedMessage(msg, signature)

    for player in CONNECTED_PLAYERS.keys():
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player]["socket"], new_msg)
        reply, signature = proto.Protocol.recv_msg(CONNECTED_PLAYERS[player]["socket"])

        sym_keys[player] = reply.sym_key

    # Enviar chaves simétricas ao Caller
    return proto.Post_Sym_Keys(None, sym_keys)


def broadcast_to_players(msg, signature):
    """
    Broadcasts a message to all Players
    :param msg:
    :return:
    """
    new_msg = proto.SignedMessage(msg, signature)

    for player in CONNECTED_PLAYERS.keys():
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player]["socket"], new_msg)


def broadcast_to_everyone(msg):
    """
    Broadcasts a message to all Users (Players + Caller)
    :param msg:
    :return:
    """
    signature = secure.sign_message(msg, PRIVATE_KEY)
    new_msg = proto.SignedMessage(msg, signature)

    for player in CONNECTED_PLAYERS.keys():
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player]["socket"], new_msg)

    proto.Protocol.send_msg(CALLER[0], new_msg)

@click.command()
@click.option('--port', '-p', type=int, required=True, help='Port to connect to the Playing Area')
def main(port):
    with socket.socket( socket.AF_INET, socket.SOCK_STREAM ) as s:
        s.bind( ('0.0.0.0', port ) )
        s.listen()
        dispatch( s )

if __name__ == '__main__':
    main()
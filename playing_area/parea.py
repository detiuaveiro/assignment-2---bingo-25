#!/bin/python

import sys
import socket
import selectors
import click
import logging
from pathlib import Path
from cryptography.hazmat.primitives import serialization

path_root = Path(__file__).parents[1]
sys.path.append(str(path_root))

import messages.protocol as proto
import security.security as secure
import security.vsc_security as vsc

CONNECTED_PLAYERS = {}                              # Dictionary holding the Connected Clients {ID: socket}
PLAYERS_INFO = {}
CALLER = {}
CALLER_WHITELIST = {"BI096890913": "ARISTIDES VAS"}
CURRENT_ID = 1
NUMBER_OF_PLAYERS = 4
PUBLIC_KEY = None
PRIVATE_KEY = None
CONTADOR = 1
NHASHED = ""

logging.basicConfig(filename='security.log', filemode='w', level=logging.INFO, \
                    format='%(seq)s - %(asctime)s - %(hash)s - %(message)s', \
                    datefmt='%m/%d/%Y %I:%M:%S %p')

def dispatch( srv_socket ):
    global PRIVATE_KEY
    global PUBLIC_KEY
    global CONTADOR
    global NHASHED

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
                try:
                    message = (None, None)
                    message = proto.Protocol.recv_msg(key.fileobj)
                    msg = message[0]
                    signature = message[1]
                    certificate = message[2]
                except:
                    msg, signature = message
                    certificate = None

                
                if signature is not None and certificate is None:
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
                            logging.info('Sent Disqualify message to caller - %s', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
                            NHASHED = "Sent Disqualify message to caller"
                            CONTADOR += 1
                
                if signature is not None and certificate is not None:
                    print("Received a certificate. Validating it...")
                    if vsc.validate_signature(signature, msg, certificate):
                        print("The signature is valid. The client will be registered.")
                        # If the signature is valid, we can proceed with the registration
                        string, reply = register_new_client(msg, certificate, key.fileobj)
                        if reply is not None:
                            print("Sending reply to client...")
                            signature = secure.sign_message(reply, PRIVATE_KEY)
                            new_msg = proto.SignedMessage(reply, signature)
                            proto.Protocol.send_msg(key.fileobj, new_msg)
                            if msg.type == "Caller":
                                logging.info('Sent %s to caller - %s ', string,  signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
                                NHASHED = "Sent " + string + "to caller"
                                CONTADOR += 1
                            else:
                                logging.info('Sent %s to player %s - %s ', string, msg.nick, signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
                                NHASHED = "Sent " + string + "to player " + msg.nick
                                CONTADOR += 1
                        continue
                    else:
                        print("The signature is not valid. The client will not be registered.")

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

    global CONTADOR
    global NHASHED

    reply = None

    if isinstance(msg, proto.Begin_Game):
        logging.info('Received Begin_Game message - %s ', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Received Begin_Game message"
        CONTADOR += 1
        # Fazer forward da Mensagem para todos os jogadores
        print("Registration process is completed!\n\nTHE GAME WILL NOW START")
        print("\nStep 1. Generation of the Playing Deck and the Player Cards")
        msg.ID = None
        signature = secure.sign_message(msg, PRIVATE_KEY)
        broadcast_to_players(msg, signature, "Begin_Game")
    elif isinstance(msg, proto.Message_Deck):
        logging.info('Received Message_Deck message - %s ', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Received Message_Deck message"
        CONTADOR += 1
        # Processo de shuffling do deck
        deck_generation(msg.deck)
    elif isinstance(msg, proto.Sign_Final_Deck_ACK):
        logging.info('Received Sign_Final_Deck_Ack message - %s ', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Received Sign_Final_Deck_Ack message"
        CONTADOR += 1

        print("\nStep 2: Validating player cards")
        # Pedir chaves simétricas a todos os Utilizadors e enviar para o Caller
        reply = share_sym_keys()

        signature = secure.sign_message(reply, PRIVATE_KEY)
        reply = proto.SignedMessage(reply, signature)
        proto.Protocol.send_msg(socket, reply)

        logging.info('Sent Post_Sym_Keys message to caller - %s ', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Sent Post_Sym_Keys message to caller"
        CONTADOR += 1

        reply = verify_playing_cards(msg.playing_cards)
    elif isinstance(msg, proto.Disqualify):
        logging.info('Received Disqualify message - %s ', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Received Disqualify message"
        CONTADOR += 1
        broadcast_to_players(msg, signature, "Disqualify")
        CONNECTED_PLAYERS.pop(int(msg.disqualified_ID))
        PLAYERS_INFO[int(msg.disqualified_ID)]["disqualified"] = True
    elif isinstance(msg, proto.Post_Final_Decks):
        logging.info('Received Post_Final_Decks message - %s ', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Received Post_Final_Decks message"
        CONTADOR += 1
        print("\nStep 3: Validating the Playing Deck")
        print("Received all decks and symmetric keys. Broadcasting to players...")
        reply = verify_playing_deck(msg, signature)

    elif isinstance(msg, proto.Ask_For_Winner):
        logging.info('Received Ask_For_Winner message - %s ', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Received Ask_For_Winner message"
        CONTADOR += 1

        print("\nStep 4: Determining the Winner")
        broadcast_to_players(msg, signature, "Ask_For_Winner")
    elif isinstance(msg, proto.Winner):
        logging.info('Received Winner message - %s ', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Received Winner message"
        CONTADOR += 1
        new_msg = proto.SignedMessage(msg, signature)
        proto.Protocol.send_msg(CALLER[0]["socket"], new_msg)
        logging.info('Sent Winner message to caller - %s', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Sent Winner message to caller"
        CONTADOR += 1
    elif isinstance(msg, proto.Winner_ACK):
        logging.info('Received Winner_ACK message - %s ', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Received Winner_ACK message"
        CONTADOR += 1
        broadcast_to_players(msg, signature, "Winner_ACK")
        print("\nThe game has succesfully finished!")
    elif isinstance(msg, proto.Get_Players_List):
        logging.info('Received Get_Players_List message - %s ', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Received Get_Players_List message"
        CONTADOR += 1
        print("Received request for Players List")
        reply = proto.Players_List(None, PLAYERS_INFO)

    if reply != None:
        signature = secure.sign_message(reply, PRIVATE_KEY)
        reply = proto.SignedMessage(reply, signature)
        proto.Protocol.send_msg(socket, reply)
        logging.info('Sent Message  - %s ', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Sent Message"
        CONTADOR += 1


def register_new_client(msg, certificate, socket):
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
    global CONTADOR
    global NHASHED
    cc_name, cc_number = vsc.get_name_and_number(certificate)

    if msg.type == "Caller":
        print("Received a Register Message from a Caller")
        if len(CALLER.keys()) > 0:
            # We already have a Caller registered in the Playing Area
            reply = proto.Register_NACK()
            string = "Register_NACK"
        else:
            print("Checking if the Caller is in the whitelist...")
            if cc_number in CALLER_WHITELIST:
                print("Caller is in the whitelist")
                if cc_name == CALLER_WHITELIST[cc_number]:
                    print("Caller name is correct")
                    CALLER[0] = {"socket": socket, "public_key": msg.pk}
                    NUMBER_OF_PLAYERS = msg.num_players
                    reply = proto.Register_ACK(0, PUBLIC_KEY)
                    string = "Register_ACK"
            else:
                print("Caller is not in the whitelist")
                reply = proto.Register_NACK()
                string = "Register_NACK"
    else:
        # User do tipo Cliente
        if len(CONNECTED_PLAYERS.keys()) > NUMBER_OF_PLAYERS or len(CALLER.keys()) == 0:
            # Refuse new player connection
            reply = proto.Register_NACK()
            string = "Register_NACK"
        else:
            CONNECTED_PLAYERS[CURRENT_ID] = {"socket": socket, "public_key": msg.pk}
            PLAYERS_INFO[CURRENT_ID] = {"nick": msg.nick, "disqualified": False, "playing_card": None, "public_key": msg.pk}
            reply = proto.Register_ACK(CURRENT_ID, PUBLIC_KEY)
            string = "Register_ACK"
            CURRENT_ID += 1

            # Redirect to the Caller player registration signed
            signature = secure.sign_message(msg, PRIVATE_KEY)
            r = proto.SignedMessage(msg, signature)
            proto.Protocol.send_msg(CALLER[0]["socket"], r)
            logging.info('Sent RegisterMessage to caller - %s', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
            NHASHED = "Sent RegisterMessage to caller"
            CONTADOR += 1

            print(f"Welcome to the Playing Area, {msg.nick}.")

    return string, reply

def deck_generation(initial_deck):
    """
    The Playing Area will redirect the initial deck created by the Caller to each Player, in turn, in order to shuffle the deck.
    During this process, the Playing Area will also receive the Playing Card form each Player
    :param initial_deck: The initial deck created by the Caller
    """
    global PRIVATE_KEY
    global CONTADOR
    global NHASHED

    print("Deck shuffling process beginning: ")
    current_deck = initial_deck

    for player in CONNECTED_PLAYERS.keys():
        # Send the Deck to the Player
        print(f"Sending deck to player {player}.")
        msg = proto.Message_Deck(None, current_deck)
        signature = secure.sign_message(msg, PRIVATE_KEY)
        new_msg = proto.SignedMessage(msg, signature)
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player]["socket"], new_msg)
        logging.info('Sent Message_Deck message to %s - %s ', player, signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Sent Message_Deck message to player " + str(player)
        CONTADOR += 1

        # Wait for the reply
        while True:
            try:
                message = (None, None)
                message = proto.Protocol.recv_msg(CONNECTED_PLAYERS[player]["socket"])
                reply = message[0]
                signature = message[1]
                certificate = message[2]
            except:
                reply, signature = message
                certificate = None

            if isinstance(reply, proto.Commit_Card):
                # If the player is sending a CHEAT message, ignore, else continue the process
                break

        # Forward the Commit Card message to the Caller
        print(
            f"Player {player} has returned their shuffled version of the deck and their playing card. Forwarding the deck to the Caller.")

        new_msg = proto.SignedMessage(reply, signature)
        proto.Protocol.send_msg(CALLER[0]["socket"], new_msg)
        logging.info('Sent Commit_Card message to caller - %s ', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Sent Commit_Card message to caller"
        CONTADOR += 1

        if isinstance(reply, proto.Commit_Card):
            current_deck = reply.deck

    # Send the final deck to the Caller
    msg = proto.Message_Deck(None, current_deck)
    signature = secure.sign_message(msg, PRIVATE_KEY)
    new_msg = proto.SignedMessage(msg, signature)
    proto.Protocol.send_msg(CALLER[0]["socket"], new_msg)
    logging.info('Sent Message_Deck message to caller - %s ', signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
    NHASHED = "Sent Message_Deck message to caller"
    CONTADOR += 1
    


def verify_playing_cards(playing_cards):
    """
    The Playing Area will receive the Playing Cards from each Player, and will verify whether they are valid or not.
    :return:
    """
    global PRIVATE_KEY
    global CONTADOR
    global NHASHED

    verified_playing_cards = {user_id : True for user_id in CONNECTED_PLAYERS.keys()}

    msg = proto.Verify_Cards(None, playing_cards)
    signature = secure.sign_message(msg, PRIVATE_KEY)
    new_msg = proto.SignedMessage(msg, signature)

    for player in CONNECTED_PLAYERS.keys():
        # Enviar a carta ao jogador
        print(f"Sending all Playing Cards to player {player}, and waiting for their validation")
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player]["socket"], new_msg)
        logging.info('Sent Verify_Cards message to player %s - %s ', str(player), signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Sent Verify_Cards message to player " + str(player)
        CONTADOR += 1
        # Esperar pela resposta 
        try:
            message = (None, None)
            message = proto.Protocol.recv_msg(CONNECTED_PLAYERS[player]["socket"])
            reply = message[0]
            signature = message[1]
            certificate = message[2]
            logging.info('Received message from player %s - %s ', player, signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
            NHASHED = "Received message from player " + str(player)
            CONTADOR += 1 
        except Exception as e:
            print(e)
            reply, signature = message
            certificate = None

        if isinstance(reply, proto.Verify_Card_NOK):
            for player in reply.users:
                print(f"Card from player {player} is invalid.")
                verified_playing_cards[int(player)] = False

        PLAYERS_INFO[int(player)]["playing_card"] = playing_cards[str(player)]
    
    # Enviar a resposta ao Caller
    return proto.Cheat_Verify(verified_playing_cards, "Cards")


def verify_playing_deck(msg, signature):
    global PRIVATE_KEY
    global CONTADOR
    global NHASHED

    players_cheated = {user_id: True for user_id in CONNECTED_PLAYERS.keys()}

    new_msg = proto.SignedMessage(msg, signature)

    for player in CONNECTED_PLAYERS.keys():
        # Enviar a carta ao jogador
        print(f"Sending playing deck to player {player}.")
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player]["socket"], new_msg)
        logging.info('Sent Post_Final_Decks message to player %s- %s ', player, signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Sent Post_Final_Decks message to player " + str(player)
        CONTADOR += 1
        # Esperar pela resposta
        try:
            message = (None, None)
            message = proto.Protocol.recv_msg(CONNECTED_PLAYERS[player]["socket"])
            reply = message[0]
            signature = message[1]
            certificate = message[2]
            logging.info('Received message from player %s- %s ', player, signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
            NHASHED = "Received message from player " + str(player)
            CONTADOR += 1
        except Exception as e:
            print(e)
            reply, signature = message
            certificate = None

        if isinstance(reply, proto.Verify_Deck_NOK):
            for player in reply.users:
                print(f"Player {player} cheated!")
                players_cheated[int(player)] = False

    # Enviar a resposta ao Caller
    return proto.Cheat_Verify(players_cheated, "Deck")

def share_sym_keys():
    global PRIVATE_KEY
    global CONTADOR
    global NHASHED 

    sym_keys = {}

    # Pedir a chave simétrica a todos os Players
    msg = proto.Ask_Sym_Keys()
    signature = secure.sign_message(msg, PRIVATE_KEY)
    new_msg = proto.SignedMessage(msg, signature)

    for player in CONNECTED_PLAYERS.keys():
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player]["socket"], new_msg)
        logging.info('Sent Ask_Sym_Keys message to player %s- %s ', player, signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Sent Ask_Sym_Keys message to player " + str(player)
        CONTADOR += 1
        try:
            message = (None, None)
            message = proto.Protocol.recv_msg(CONNECTED_PLAYERS[player]["socket"])
            reply = message[0]
            signature = message[1]
            certificate = message[2]
            logging.info('Received message from player %s- %s ', player, signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
            NHASHED = "Received message from player " + str(player)
            CONTADOR += 1
        except Exception as e:
            print(e)
            reply, signature = message
            certificate = None

        sym_keys[player] = reply.sym_key

    # Enviar chaves simétricas ao Caller
    return proto.Post_Sym_Keys(None, sym_keys)


def broadcast_to_players(msg, signature, string):
    """
    Broadcasts a message to all Players
    :param msg:
    :return:
    """
    global CONTADOR
    global NHASHED

    new_msg = proto.SignedMessage(msg, signature)

    for player in CONNECTED_PLAYERS.keys():
        proto.Protocol.send_msg(CONNECTED_PLAYERS[player]["socket"], new_msg)
        logging.info('Sent %s message to player %s - %s ', string, player, signature, extra={'seq': CONTADOR, 'hash': hash(NHASHED)})
        NHASHED = "Sent " + string + " message to player " + str(player)
        CONTADOR += 1


@click.command()
@click.option('--port', '-p', type=int, required=True, help='Port to connect to the Playing Area')
def main(port):
    with socket.socket( socket.AF_INET, socket.SOCK_STREAM ) as s:
        s.bind( ('0.0.0.0', port ) )
        s.listen()
        dispatch( s )

if __name__ == '__main__':
    main()
#!/bin/python
import selectors
import sys
import socket
import json
import random
from pathlib import Path

path_root = Path(__file__).parents[1]
sys.path.append(str(path_root))

import messages.protocol as proto
import security.security as secure


class Player:
    ADDRESS = '127.0.0.1'

    def __init__(self, nick: str, port):
        # Personal Information
        self.nick = nick
        self.ID = None
        self.port = port

        # Generated Keys
        self.private_key = None
        self.public_key = None
        self.sym_key = None

        # Game Information
        self.N = 0                                                              # Size of the Playing Deck
        self.players_info = {}                                                  # Info about the Players
        self.card = []                                                          # My playing card
        self.playing_deck = []                                                  # Playing Deck in plaintext form
        self.playing_area_pk = None                                             # Playing Area Public Key

        # Socket and Selector creation
        self.selector = selectors.DefaultSelector()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        

    def connect(self):
        """
        Function used to connect the created Socket to the Playing Area. The port passed in the command-line as an argument to this script should be the port where the Playing Area runs.
        """
        # Conexão à socket da Playing Area
        self.socket.connect((self.ADDRESS, self.port))
        self.selector.register(self.socket, selectors.EVENT_READ, self.read_data)

        # Gerar par de chaves assimétricas
        self.generate_keys()

        # Envio da Register Message à Playing Area
        message = proto.RegisterMessage("Player", self.public_key, nick=self.nick)
        proto.Protocol.send_msg(self.socket, message)

        # Verificação da resposta recebida
        msg = proto.Protocol.recv_msg(self.socket)

        if isinstance(msg, proto.Register_NACK):
            # Playing Area rejeitou Player
            print("Register Rejected")
            print("Shutting down...")
            exit()
        elif isinstance(msg, proto.Register_ACK):
            self.ID = msg.ID
            self.playing_area_pk = msg.pk
            print("Register Accepted")

    def read_data(self, socket):
        """
        This function will determine the class of the received Message, and call the code that should be executed when an instance of this Message is received
        :param socket: The calling socket
        :return:
        """
        msg, signature = proto.Protocol.recv_msg(socket)
        print(msg)
        print(signature)

        # Verify if the signature of the message belongs to the Playing Area
        if not secure.verify_signature(msg, signature, self.playing_area_pk):
            # If the Playing Area signature is faked, the game is compromised
            print("The Playing Area signature was forged! The game is compromised.")
            print("Shutting down...")
            self.selector.unregister(socket)
            socket.close()
            exit()

        reply = None

        # Depending on the type of Message received, decide what to do
        if isinstance(msg, proto.Begin_Game):
            #TODO: Guardar as chaves públicas de todos os jogadores
            print("The game is starting...")
            pass
        elif isinstance(msg, proto.Message_Deck):
            self.N = len(msg.deck)

            print("Shuffling Deck...")
            suffled_deck = self.shuffle_deck(msg.deck)
            print("Generating Playing Card...")

            ''' implementation of one of the cheating systems'''
            rand = random.randint(0, 100)
            if rand>10:
                self.generate_playing_card()
            else:
                self.generate_cheating_card(suffled_deck)

                #ADAPTAR DEPOIS AO PROTOCOLO E VARIAVEIS DEFINIDAS - TODO!!!!!!!!
                cheat_message = proto.Cheat(self.ID)
                signature = secure.sign_message(cheat_message, self.private_key)
                new_message = proto.SignedMessage(cheat_message, signature)
                proto.Protocol.send_msg(socket, new_message )

            reply = proto.Commit_Card(self.ID, suffled_deck, self.card)
        elif isinstance(msg, proto.Verify_Cards):
            # Initiate Playing Cards verification process
            reply = self.verify_cards(msg)
        elif isinstance(msg, proto.Disqualify):
            # Someone has been disqualified
            if msg.disqualified_ID == self.ID:
                # I have been disqualified
                self.selector.unregister(socket)
                socket.close()
                print('I have been disqualified. Exiting...')
                exit()
            else:
                # Someone else was disqualified
                print(f"Player {msg.disqualified_ID} has been disqualified.")
                self.players_info.pop(msg.disqualified_ID)
        elif isinstance(msg, proto.Ask_Sym_Keys):
            print("Sending my symmetric key...")
            reply = proto.Post_Sym_Keys(self.ID, self.sym_key)
        elif isinstance(msg, proto.Post_Final_Decks):
            print("Starting Deck decryption process...")
            reply = self.decrypt(msg.decks, msg.signed_deck)
        elif isinstance(msg, proto.Ask_For_Winner):
            reply = self.find_winner()
        elif isinstance(msg, proto.Winner_ACK):
            if msg.ID_winner == self.ID:
                print("Bingo! I'm a winner, baby")
            else:
                print(f"{msg.ID_winner} you're a winner, baby")
        else:
            self.selector.unregister(socket)
            socket.close()
            print('Connection to Playing Area lost')
            exit()

        if reply is not None:
            # There is a message to be sent
            signature = secure.sign_message(reply, self.private_key)
            new_message = proto.SignedMessage(reply, signature)
            proto.Protocol.send_msg(socket, new_message)

    def generate_keys(self):
        """
        Function responsible for the generation of this User's assymetric key pair
        :return:
        """
        self.private_key, self.public_key = secure.gen_assymetric_key

    def shuffle_deck(self, deck):
        """
        Function responsible for the shuffling of the Playing Deck
        :return:
        """
        #TODO: Encrypt the numbers in the deck
        self.sym_key = secure.gen_symmetric_key()
        return random.sample(deck, len(deck))

    def generate_playing_card(self):
        """
        Function responsible for the generation of the Playing Deck
        :return:
        """
        self.card = random.sample(list(range(1, self.N + 1)), int(self.N/4))

    def generate_cheating_card(self, deck):
        '''creating a smaller deck where it consists of the first value of the deck repeated several times'''
        self.card = random.sample(deck[0], int(self.N/8))

    def verify_cards(self, msg):
        cheaters = []

        for player in msg.playing_cards.keys():
            if int(player) == self.ID:
                continue

            #TODO: Verificar assinatura
            print(f"Verifying Player {player}'s Playing Card")

            if len(set(msg.playing_cards[player])) != int(self.N/4):
                print(f"Player {player} has cheated!")
                cheaters.append(player)

            self.players_info[int(player)] = {"card": msg.playing_cards[player]}

        if len(cheaters) > 0:
            return proto.Verify_Card_NOK(self.ID, cheaters)
        else:
            print("Nobody has cheated")
            return proto.Verify_Card_OK(self.ID)

    def decrypt(self, decks, signed_deck):
        #TODO: Verificar assinatura do Caller no sign_deck

        keys = sorted(decks, reverse=True)
        current_deck = list()
        cheaters = []

        # We start the decryption process by taking the Deck encrypted by the player with the highest ID, and working all the way down to the lowest ID
        for i in range(len(keys)):
            if i != 0:
                # If there's a difference between the deck received in this step, and the deck determined after decryption in the previous step, the previous player cheated
                # The only being compared is if the set of numbers in both decks are matching - order doesn't matter
                dif = set(current_deck).difference(set(decks[keys[i]]["deck"]))
                print(dif)

                if len(dif) > 0:
                    cheaters.append(keys[i-1])
                    print(f"Player {keys[i - 1]} cheated!")

            print(decks[keys[i]]["deck"])
            print(decks[keys[i]]["sym_key"])
            # TODO: Desincriptar e verificar assinatura

            # The new current_deck will be the deck resulting from the decryption of the deck signed by the current player being analysed
            current_deck = decks[keys[i]]["deck"]  # TODO: substituir pelo deck desincreptado

        print("Final plaintext Deck: " + str(current_deck))

        # The playing deck is the plaintext deck obtained at the end of the decryption process
        # self.playing_deck = current_deck
        self.playing_deck = signed_deck  # TODO: Substituir pela versão comentada

        if len(cheaters) > 0:
            return proto.Verify_Deck_NOK(self.ID, cheaters)
        else:
            print("Nobody has cheated")
            return proto.Verify_Deck_OK(self.ID)

    def find_winner(self):
        winner = None

        for number in self.playing_deck:
            if number in self.card:
                self.card.remove(number)

            if len(self.card) == 0:
                winner = self.ID

            for player in self.players_info.keys():
                if number in self.players_info[player]["card"]:
                    self.players_info[player]["card"].remove(number)

                if len(self.players_info[player]["card"]) == 0:
                    winner = player
                    break

            if winner is not None:
                break

        print(f"I determined {winner} as a winner, baby")
        return proto.Winner(self.ID, winner)

    def loop(self):
        while True:
            events = self.selector.select(timeout=None)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj)

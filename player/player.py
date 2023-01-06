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
        self.nick = nick
        self.N = 0                                                              # Números a considerar na geração do Playing Deck
        self.players_info = {}                                                  # Dicionário que vai guardar info de todos os jogadores
        self.id = None

        self.card = []
        self.playing_deck = []                                                  # Versão plaintext do Playing Deck

        # Criação da Socket e do Selector
        self.selector = selectors.DefaultSelector()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.port = port
        

    def connect(self):
        """
                Function used to connect the created Socket to the Playing Area. The port passed in the command-line as an argument to this script should be the port where the Playing Area runs.
                """
        # Conexão à socket da Playing Area
        self.socket.connect((self.ADDRESS, self.port))
        self.selector.register(self.socket, selectors.EVENT_READ, self.read_data)

        # Envio da Register Message à Playing Area
        message = proto.RegisterMessage("Player", nick=self.nick)
        proto.Protocol.send_msg(self.socket, message)

        # Verificação da resposta recebida
        msg = proto.Protocol.recv_msg(self.socket)

        if isinstance(msg, proto.Register_NACK):
            # Playing Area rejeitou Player
            print("Register Rejected")
            print("Shutting down...")
            exit()
        elif isinstance(msg, proto.Register_ACK):
            self.id = msg.id
            print("Register Accepted")

        # Se o registo foi bem sucedido, gerar par de chaves assimétricas
        self.generate_keys()

    def read_data(self, socket):
        """
        This function will determine the class of the received Message, and call the code that should be executed when an instance of this Message is received
        :param socket: The calling socket
        :return:
        """
        msg = proto.Protocol.recv_msg(socket)
        print(msg)

        reply = None
        if isinstance(msg, proto.Begin_Game):
            #TODO: Guardar as chaves públicas de todos os jogadores
            print("The game is starting...")
            pass
        elif isinstance(msg, proto.Message_Deck):
            self.N = len(msg.deck)

            print("Shuffling Deck...")
            suffled_deck = self.shuffle_deck(msg.deck)

            print("Generating Playing Card...")
            self.generate_playing_card()
            reply = proto.Commit_Card(suffled_deck, self.card)
        elif isinstance(msg, proto.Verify_Cards):
            # Initiate Playing Cards verification process
            reply = self.verify_cards(msg)
        elif isinstance(msg, proto.Disqualify):
            # Someone has been disqualified
            if msg.id_user == self.id:
                # I have been disqualified
                self.selector.unregister(socket)
                socket.close()
                print('I have been disqualified. Exiting...')
                exit()
            else:
                # Someone else was disqualified
                print(f"Player {msg.id_user} has been disqualified.")
                self.players_info.pop(msg.id_user)
        elif isinstance(msg, proto.Ask_Sym_Keys):
            print("Sending my symmetric key...")
            reply = proto.Post_Sym_Keys("chave")
        elif isinstance(msg, proto.Post_Final_Decks):
            print("Starting Deck decryption process...")
            reply = self.decrypt(msg.decks, msg.signed_deck)
        elif isinstance(msg, proto.Ask_For_Winner):
            reply = self.find_winner()
        elif isinstance(msg, proto.Winner_ACK):
            if msg.id_user == self.id:
                print("Bingo! I'm a winner, baby")
            else:
                print(f"{msg.id_user} you're a winner, baby")
        else:
            self.selector.unregister(socket)
            socket.close()
            print('Connection to Playing Area lost')
            exit()

        if reply is not None:
            proto.Protocol.send_msg(socket, reply)

    def generate_keys(self):
        """
        Function responsible for the generation of this User's assymetric key pair
        :return:
        """
        self.private_key, self.public_key =secure.gen_assymetric_key
        return self.private_key, self.public_key
        pass

    def shuffle_deck(self, deck):
        """
        Function responsible for the shuffling of the Playing Deck
        :return:
        """
        #TODO: Encrypt the numbers in the deck
        return random.sample(deck, len(deck))

    def generate_playing_card(self):
        """
        Function responsible for the generation of the Playing Deck
        :return:
        """
        self.card = random.sample(list(range(1, self.N + 1)), int(self.N/4))

    def verify_cards(self, msg):
        cheaters = []

        for player in msg.playing_cards.keys():
            if int(player) == self.id:
                continue

            #TODO: Verificar assinatura
            print(f"Verifying Player {player}'s Playing Card")

            if len(set(msg.playing_cards[player])) != int(self.N/4):
                print(f"Player {player} has cheated!")
                cheaters.append(player)

            self.players_info[int(player)] = {"card": msg.playing_cards[player]}

        if len(cheaters) > 0:
            return proto.Verify_Card_NOK(cheaters)
        else:
            print("Nobody has cheated")
            return proto.Verify_Card_OK()

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
            return proto.Verify_Deck_NOK(cheaters)
        else:
            print("Nobody has cheated")
            return proto.Verify_Deck_OK()

    def find_winner(self):
        winner = None

        for number in self.playing_deck:
            if number in self.card:
                self.card.remove(number)

            if len(self.card) == 0:
                winner = self.id

            for player in self.players_info.keys():
                if number in self.players_info[player]["card"]:
                    self.players_info[player]["card"].remove(number)

                if len(self.players_info[player]["card"]) == 0:
                    winner = player
                    break

            if winner is not None:
                break

        print(f"I determined {winner} as a winner, baby")
        return proto.Winner(self.id, winner)

    def loop(self):
        while True:
            events = self.selector.select(timeout=None)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj)

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


class Player:
    ADDRESS = '127.0.0.1'

    def __init__(self, nick: str, port):
        self.nick = nick
        self.N = 0                                                              # Números a considerar na geração do Playing Deck
        self.players_info = {}                                                  # Dicionário que vai guardar info de todos os jogadores

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
            print("Register Accepted")

        # Se o registo foi bem sucedido, gerar par de chaves assimétricas
        self.generate_keys()

    def generate_keys(self):
        """
        Function responsible for the generation of this User's assymetric key pair
        :return:
        """
        pass

    def shuffle_deck(self, deck):
        """
        Function responsible for the shuffling of the Playing Deck
        :return:
        """
        #TODO: Encrypt the numbers in the deck
        return random.sample(deck, len(deck))

    def generate_playing_card(self, N):
        """
        Function responsible for the generation of the Playing Deck
        :return:
        """
        return random.sample(list(range(1, N + 1)), int(N/4))

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
            playing_card = self.generate_playing_card(self.N)

            reply = proto.Commit_Card(suffled_deck, playing_card) 
        elif isinstance(msg, proto.Verify_Cards):
            pass
        else:
            self.selector.unregister(socket)
            socket.close()
            print('Connection to Playing Area lost')
            exit()

        if reply is not None:
            proto.Protocol.send_msg(socket, reply)

    def loop(self):
        while True:
            events = self.selector.select(timeout=None)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj)

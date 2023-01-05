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


class Caller:
    ADDRESS = '127.0.0.1'

    def __init__(self, nick: str, port, N = 60, players = 4):
        self.nick = nick
        self.port = port
        self.number_of_players = players
        self.PLAYERS = {}
        self.player_counter = 0
        self.N = N                                                              # Números a considerar na geração do Playing Deck

        self.deck = []

        # Criação da Socket e do Selector
        self.selector = selectors.DefaultSelector()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


    def connect(self):
        """
        Function used to connect the created Socket to the Playing Area. The port passed in the command-line as an argument to this script should be the port where the Playing Area runs.
        """
        # Conexão à socket da Playing Area
        self.socket.connect( (self.ADDRESS, self.port))
        self.selector.register(self.socket, selectors.EVENT_READ, self.read_data)

        # Envio da Register Message à Playing Area
        message = proto.RegisterMessage("Caller", nick=self.nick, num_players=self.number_of_players)
        proto.Protocol.send_msg(self.socket, message)

        # Verificação da resposta recebida
        msg = proto.Protocol.recv_msg(self.socket)

        if isinstance(msg, proto.Register_NACK):
            # Playing Area rejeitou Caller
            print("Register Rejected")
            print("Shutting down...")
            exit()
        elif isinstance(msg, proto.Register_ACK):
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

        if isinstance(msg, proto.RegisterMessage):
            # REGISTER MESSAGE WITH PLAYER INFORMATION
            self.player_counter += 1
            self.PLAYERS[self.player_counter] = {"nick": msg.nick}
            if self.player_counter == self.number_of_players:
                # Atingido limite de jogadores: Mandar mensagem BEGIN GAME para a Playing Area
                print("The limit of available players has been reached. I will now start the game.")
                reply = proto.Begin_Game()
                proto.Protocol.send_msg(socket, reply)

                # Gerar o deck e criar a mensagem para enviá-lo
                reply = self.generate_deck()
        elif isinstance(msg, proto.Commit_Card):
            self.PLAYERS[msg.id_user]["card"] = msg.card
            self.PLAYERS[msg.id_user]["cheated"] = False
            self.PLAYERS[msg.id_user]["deck"] = msg.deck
        elif isinstance(msg, proto.Message_Deck):
            # RECEIVED THE PLAYING DECK
            self.deck = msg.deck
            #TODO: Desencriptar cada número
            #TODO: Assinar o deck final
            print("Signing the Final Deck...")
            reply = proto.Sign_Final_Deck_ACK({user_id: self.PLAYERS[user_id]["card"] for user_id in self.PLAYERS})

            print("Starting Playing Cards validation process...")
            self.verify_cards()
        elif isinstance(msg, proto.Verified_Cards):
            # Verify if another Player detected cheating
            for player in msg.verified_playing_cards:
                if not msg.verified_playing_cards[player]:
                    self.PLAYERS[player]["cheated"] = True

            # If a player has cheated, disqualify them
            for player in self.PLAYERS:
                if self.PLAYERS[player]["cheated"]:
                    print(f"Player {player} has been disqualified.")
                    proto.Protocol.send_msg(socket, proto.Disqualify(player))
        else:
            self.selector.unregister(socket)
            socket.close()
            print('Connection to Playing Area lost')
            exit()

        if reply != None:
            proto.Protocol.send_msg(socket, reply)

    def generate_keys(self):
        """
        Function responsible for the generation of this User's assymetric key pair
        :return:
        """
        pass

    def generate_deck(self):
        """
        Function that will create the set of N numbers, to be shuffled by all the Players of the game.
        """
        #TODO: Encriptar cada número
        print("Creating the Playing Deck...")
        self.deck = random.sample(list(range(self.N)), self.N)

        # Criar mensagem do tipo POST_INITIAL_DECK
        return proto.Message_Deck(self.deck)

    def verify_cards(self):
        for player in self.PLAYERS.keys():
            #TODO: Verificar assinatura
            print(f"Verifying Player {player}'s Playing Card")

            if len(set(self.PLAYERS[player]["card"])) != int(self.N/4):
                print(f"Player {player} has cheated!")
                self.PLAYERS[player]["cheated"] = True


    def loop(self):
        while True:
            events = self.selector.select(timeout=None)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj)

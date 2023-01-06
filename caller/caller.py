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

class Caller:
    ADDRESS = '127.0.0.1'

    def __init__(self, nick: str, port, N = 60, players = 4):
        self.nick = nick
        self.port = port
        self.number_of_players = players
        self.PLAYERS = {}
        self.player_counter = 0
        self.N = N                                                              # Números a considerar na geração do Playing Deck

        self.initial_deck = []                                                  # Deck obtido pelo Caller após fazer shuffle no 1º passo de criaçã do Deck
        self.signed_final_deck = []                                             # Deck assinado pelo Caller no final do processo de criação do Deck
        self.playing_deck = []                                                  # Versão plaintext do Playing Deck
        self.winner = None

        self.public_key = None
        self.private_key = None
        self.sym_key = None

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
            #TODO: Assinar o deck final
            self.signed_final_deck = msg.deck
            print("Signing the Final Deck...")
            reply = proto.Sign_Final_Deck_ACK({user_id: self.PLAYERS[user_id]["card"] for user_id in self.PLAYERS.keys()})

            print("Starting Playing Cards validation process...")
            self.verify_cards()
        elif isinstance(msg, proto.Cheat_Verify):
            # Verify if another Player detected cheating
            for player in msg.cheaters:
                if not msg.cheaters[player]:
                    self.PLAYERS[int(player)]["cheated"] = True

            # If a player has cheated, disqualify them
            for player in self.PLAYERS:
                if self.PLAYERS[int(player)]["cheated"]:
                    print(f"Player {player} has been disqualified.")
                    proto.Protocol.send_msg(socket, proto.Disqualify(player))
                    self.PLAYERS.pop(player)

            if msg.stage == "Cards":
                print("Verification process completed")
                reply = proto.Cards_Validated()
            else:
                print("Deck Validation completed")
                reply = proto.Ask_For_Winner()
                self.find_winner()
        elif isinstance(msg, proto.Post_Sym_Keys):
            # Symmetric keys of all Players in the games
            print("Received the symmetric keys of other Players")
            for player in msg.sym_key.keys():
                self.PLAYERS[int(player)]["sym_key"] = msg.sym_key[player]

            info = {}
            info[0] = {"deck": self.initial_deck, "sym_key": self.sym_key}
            for player in self.PLAYERS.keys():
                info[player] = {"deck": self.PLAYERS[int(player)]["deck"], "sym_key": self.PLAYERS[int(player)]["sym_key"]}

            reply = proto.Post_Final_Decks(info, self.signed_final_deck)

            print("Starting Deck decryption")
            self.decrypt(info)
        elif isinstance(msg, proto.Winner):
            if msg.id_winner != self.winner:
                proto.Protocol.send_msg(socket, proto.Disqualify(msg.id))
                self.PLAYERS.pop(int(msg.id))
                print(f"Player {msg.id} has been disqualified")
            else:
                self.PLAYERS[int(msg.id)]["winner"] = True

            finished = True
            for player in self.PLAYERS:
                if "winner" not in self.PLAYERS[player].keys():
                    finished = False
                    break

            if finished:
                print(f"The official winner is {self.winner}")
                reply = proto.Winner_ACK(self.winner)
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
        self.private_key, self.public_key =secure.gen_assymetric_key
        return self.private_key, self.public_key

    def generate_deck(self):
        """
        Function that will create the set of N numbers, to be shuffled by all the Players of the game.
        """
        #TODO: Encriptar cada número
        print("Creating the Playing Deck...")
        self.initial_deck = random.sample(list(range(self.N)), self.N)

        # Criar mensagem do tipo POST_INITIAL_DECK
        return proto.Message_Deck(self.initial_deck)

    def verify_cards(self):
        for player in self.PLAYERS.keys():
            #TODO: Verificar assinatura
            print(f"Verifying Player {player}'s Playing Card")

            if len(set(self.PLAYERS[player]["card"])) != int(self.N/4):
                print(f"Player {player} has cheated!")
                self.PLAYERS[player]["cheated"] = True

    def decrypt(self, decks):
        keys = sorted(decks, reverse=True)
        current_deck = list()

        # We start the decryption process by taking the Deck encrypted by the player with the highest ID, and working all the way down to the lowest ID
        for i in range(len(keys)):
            if i != 0:
                # If there's a difference between the deck received in this step, and the deck determined after decryption in the previous step, the previous player cheated
                # The only being compared is if the set of numbers in both decks are matching - order doesn't matter
                dif = set(current_deck).difference(set(decks[keys[i]]["deck"]))
                print(dif)

                if len(dif) > 0:
                    self.PLAYERS[keys[i-1]]["cheated"] = True
                    print(f"Player {keys[i-1]} cheated!")

            print(decks[keys[i]]["deck"])
            print(decks[keys[i]]["sym_key"])
            #TODO: Desincriptar e verificar assinatura

            # The new current_deck will be the deck resulting from the decryption of the deck signed by the current player being analysed
            current_deck = decks[keys[i]]["deck"]           #TODO: substituir pelo deck desincreptado

        print("Final plaintext Deck: " + str(current_deck))

        # The playing deck is the plaintext deck obtained at the end of the decryption process
        #self.playing_deck = current_deck
        self.playing_deck = self.signed_final_deck          #TODO: Substituir pela versão comentada

    def find_winner(self):
        for number in self.playing_deck:
            for player in self.PLAYERS.keys():
                if number in self.PLAYERS[player]["card"]:
                    self.PLAYERS[player]["card"].remove(number)

                if len(self.PLAYERS[player]["card"]) == 0:
                    self.winner = player
                    break

            if self.winner is not None:
                break

        print(f"I determined {self.winner} as a winner, baby")

    def loop(self):
        while True:
            events = self.selector.select(timeout=None)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj)

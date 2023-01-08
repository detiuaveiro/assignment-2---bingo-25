#!/bin/python
import base64
import selectors
import sys
import socket
import random
from pathlib import Path
from cryptography.hazmat.primitives import serialization

path_root = Path(__file__).parents[1]
sys.path.append(str(path_root))

import messages.protocol as proto
import security.security as secure
import security.vsc_security as vsc

class Caller:
    ADDRESS = '127.0.0.1'

    def __init__(self, nick: str, port, N = 60, players = 4):
        # Personal Information
        self.nick = nick
        self.port = port
        self.ID = 0

        # Generated Keys
        self.private_key = None
        self.public_key = None
        self.sym_key = None

        # Game Information
        self.number_of_players = players
        self.PLAYERS = {}                                                       # Information about Players
        self.player_counter = 0                                                 # Counts already registered Players
        self.winners = []                                                       # The determined winners
        self.playing_area_pk = None                                             # Playing Area Public Key

        # Playing Deck Information
        self.N = N                                                              # Size of the Playing Deck
        self.initial_deck = []                                                  # Deck after shuffling in the first step of the shuffling process
        self.signed_final_deck = []                                             # Signed Deck at the end of the shuffling process
        self.playing_deck = []                                                  # Plaintext version of the final Playing Deck

        # Socket and Selector creation
        self.selector = selectors.DefaultSelector()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


    def connect(self):
        """
        Function used to connect the created Socket to the Playing Area. The port passed in the command-line as an argument to this script should be the port where the Playing Area runs.
        """
        # Conexão à socket da Playing Area
        self.socket.connect( (self.ADDRESS, self.port))
        self.selector.register(self.socket, selectors.EVENT_READ, self.read_data)

        # Gerar par de chaves assimétricas
        self.generate_keys()

        # Envio da Register Message à Playing Area
        message = proto.RegisterMessage("Caller", self.public_key, nick=self.nick, num_players=self.number_of_players)
        signature = vsc.sign_message(message)
        certificate = vsc.get_cert_data()    

        cert_message = proto.CertMessage(message, signature, certificate)
        proto.Protocol.send_msg(self.socket, cert_message)

        # Verificação da resposta recebida
        msg, signature, certificate = proto.Protocol.recv_msg(self.socket)

        if isinstance(msg, proto.Register_NACK):
            # Playing Area rejeitou Caller
            print("Register Rejected")
            print("Shutting down...")
            exit()
        elif isinstance(msg, proto.Register_ACK):
            if not secure.verify_signature(msg, signature, msg.pk):
                # Playing Area signature is faked
                print("The Playing Area signature was forged! The game is compromised.")
                print("Shutting down...")
                exit()
            else:
                self.playing_area_pk = msg.pk
                print("Register Accepted")


    def read_data(self, socket):
        """
        This function will determine the class of the received Message, and call the code that should be executed when an instance of this Message is received
        :param socket: The calling socket
        :return:
        """
        msg, signature, certificate = proto.Protocol.recv_msg(socket)
        print(f"Received message: {msg} Signature: {signature}")

        # Verify if the signature of the message belongs to the Playing Area
        if signature is not None:
            if not secure.verify_signature(msg, signature, self.playing_area_pk):
                # If the Playing Area signature is faked, the game is compromised
                print("The Playing Area signature was forged! The game is compromised.")
                print("Shutting down...")
                self.selector.unregister(socket)
                socket.close()
                exit()

        reply = None

        if isinstance(msg, proto.RegisterMessage):
            # REGISTER MESSAGE WITH PLAYER INFORMATION
            self.player_counter += 1
            self.PLAYERS[self.player_counter] = {"nick": msg.nick, "pk": msg.pk}

            print(f"Registered Player {self.player_counter} with nick {msg.nick}")
            if self.player_counter == self.number_of_players:
                # Atingido limite de jogadores: Mandar mensagem BEGIN GAME para a Playing Area
                print("The limit of available players has been reached. I will now start the game.")

                # Create the Begin Game Message
                msg = proto.Begin_Game(self.ID, {user_id: self.PLAYERS[user_id]["pk"] for user_id in self.PLAYERS.keys()})
                signature = secure.sign_message(msg, self.private_key)
                reply = proto.SignedMessage(msg, signature)

                proto.Protocol.send_msg(socket, reply)

                # Gerar o deck e criar a mensagem para enviá-lo
                reply = self.generate_deck()
        elif isinstance(msg, proto.Commit_Card):
            self.PLAYERS[msg.ID]["card"] = msg.card
            self.PLAYERS[msg.ID]["cheated"] = False
            self.PLAYERS[msg.ID]["deck"] = msg.deck
        elif isinstance(msg, proto.Message_Deck):
            # RECEIVED THE PLAYING DECK
            self.signed_final_deck = msg.deck
            print("Signing the Final Deck...")
            reply = proto.Sign_Final_Deck_ACK(self.ID, {user_id: self.PLAYERS[user_id]["card"] for user_id in self.PLAYERS.keys()})

            print("\nStep 2")
            print("Starting the process of validating Playing Cards...")
            self.verify_cards()
        elif isinstance(msg, proto.Cheat_Verify):
            # Verify if another Player detected cheating
            for player in msg.cheaters:
                if not msg.cheaters[player]:
                    self.PLAYERS[int(player)]["cheated"] = True

            # If a player has cheated, disqualify them
            cheaters = []

            for player in self.PLAYERS:
                if self.PLAYERS[int(player)]["cheated"]:
                    cheaters.append(int(player))

            for player in cheaters:
                self.disqualify_player(int(player))

            if msg.stage == "Cards":
                print("Verification process completed")
                reply = proto.Cards_Validated(self.ID)
            else:
                print("Deck Validation completed")
                reply = proto.Ask_For_Winner(self.ID)
                self.find_winner()
        elif isinstance(msg, proto.Post_Sym_Keys):
            # Symmetric keys of all Players in the games
            print("\nStep 3")
            print("Received the symmetric keys of the Players")
            for player in msg.sym_key.keys():
                self.PLAYERS[int(player)]["sym_key"] = msg.sym_key[player]

            info = {}
            info[0] = {"deck": self.initial_deck, "sym_key": self.sym_key}
            for player in self.PLAYERS.keys():
                info[player] = {"deck": self.PLAYERS[int(player)]["deck"], "sym_key": self.PLAYERS[int(player)]["sym_key"]}

            reply = proto.Post_Final_Decks(self.ID, info, self.signed_final_deck)

            print("I will now start to decrypt the Deck and verify if anyone cheated")
            self.decrypt(info)
        elif isinstance(msg, proto.Winner):
            if set([int(id) for id in msg.ID_winner]) != set(self.winners):
                # The player has provided the wrong winners
                self.disqualify_player(int(msg.ID))
            else:
                self.PLAYERS[int(msg.ID)]["winner"] = True

            finished = True
            for player in self.PLAYERS:
                if "winner" not in self.PLAYERS[player].keys():
                    finished = False
                    break

            if finished:
                print("\nThe official winners are:")
                for person in self.winners:
                    nick = self.PLAYERS[person]["nick"]
                    print(f"-> Player #{person}, {nick}")
                print("Congratulations!")
                reply = proto.Winner_ACK(self.ID, self.winners)
        elif isinstance(msg, proto.Ask_Sym_Keys):
            sk = base64.b64encode(self.sym_key).decode()
            reply = proto.Post_Sym_Keys(self.ID, sk)
        elif isinstance(msg, proto.Disqualify):
            # The PA as warned the Caller that someone forged a signature
            print(f"Player {msg.disqualified_ID} has forged a signature. They are now disqualified")
            self.disqualify_player(int(msg.disqualified_ID))
        else:
            self.selector.unregister(socket)
            socket.close()
            print('Connection to Playing Area lost')
            exit()

        if reply != None:
            # There is a message to be sent
            signature = secure.sign_message(reply, self.private_key)
            new_message = proto.SignedMessage(reply, signature)
            proto.Protocol.send_msg(socket, new_message)

    def generate_keys(self):
        """
        Function responsible for the generation of this User's assymetric key pair
        :return:
        """
        self.private_key, self.public_key = secure.gen_assymetric_key()

    def generate_deck(self):
        """
        Function that will create the set of N numbers, to be shuffled by all the Players of the game.
        """
        print("\nStep 1")
        print("Creating the Playing Deck...")
        self.sym_key = secure.gen_symmetric_key()
        self.initial_deck = random.sample(list(range(self.N)), self.N)

        deck = list()
        for number in self.initial_deck:
            encrypted_number = base64.b64encode(secure.encrypt_number(number, self.sym_key)).decode('utf-8')
            deck.append(encrypted_number)

        self.initial_deck = deck
        self.sym_key = base64.b64encode(self.sym_key).decode('utf-8')

        # Criar mensagem do tipo POST_INITIAL_DECK
        return proto.Message_Deck(self.ID, deck)


    def verify_cards(self):
        for player in self.PLAYERS.keys():
            nick = self.PLAYERS[player]["nick"]
            print(f"Verifying Player {nick}'s Playing Card")

            if len(set(self.PLAYERS[player]["card"])) != int(self.N/4):
                print(f"Player {nick} has cheated!")
                self.PLAYERS[player]["cheated"] = True

    def decrypt(self, decks):
        keys = sorted(decks, reverse=True)
        current_deck = list()

        print(keys)

        # We start the decryption process by taking the Deck encrypted by the player with the highest ID, and working all the way down to the lowest ID
        for i in range(len(keys)):
            if i != 0:
                # If there's a difference between the deck received in this step, and the deck determined after decryption in the previous step, the previous player cheated
                # The only being compared is if the set of numbers in both decks are matching - order doesn't matter
                dif = set(current_deck).difference(set([base64.b64decode(number) for number in decks[keys[i]]["deck"]]))

                if len(dif) > 0:
                    self.PLAYERS[keys[i-1]]["cheated"] = True
                    nick = self.PLAYERS[keys[i-1]]["nick"]
                    print(f"Player {keys[i-1]}, {nick}, cheated!")

            new_deck = list()
            for number in decks[keys[i]]["deck"]:
                flag = 1 if keys[i] == 0 else 0
                decrypted_number = secure.decrypt_number(base64.b64decode(number), base64.b64decode(decks[keys[i]]["sym_key"]), flag)
                new_deck.append(decrypted_number)

            # The new current_deck will be the deck resulting from the decryption of the deck signed by the current player being analysed
            current_deck = new_deck 

        print("Final plaintext Deck: " + str(current_deck))

        # The playing deck is the plaintext deck obtained at the end of the decryption process
        #self.playing_deck = current_deck
        self.playing_deck = current_deck

    def find_winner(self):
        print("\nStep 4")
        print("I will now call out all the numbers, and find the winner:")
        counter = 0
        for number in self.playing_deck:
            counter += 1
            print(f"#{counter}: {number}")
            for player in self.PLAYERS.keys():
                if number in self.PLAYERS[player]["card"]:
                    self.PLAYERS[player]["card"].remove(number)

                if len(self.PLAYERS[player]["card"]) == 0:
                    self.winners.append(player)

            if len(self.winners) != 0:
                break

        for person in self.winners:
            print(f"\nI determined {person} as a winner")

    def disqualify_player(self, player):
        """

        """
        nick = self.PLAYERS[player]["nick"]
        print(f"Player #{player}, {nick}, has been disqualified.")

        # Create DISQUALIFY message
        dsq_message = proto.Disqualify(player, self.ID)
        signature = secure.sign_message(dsq_message, self.private_key)
        new_message = proto.SignedMessage(dsq_message, signature)
        proto.Protocol.send_msg(self.socket, new_message)

        # Eliminate info about the player
        self.PLAYERS.pop(int(player))

        # If the play is in the winners list, take them off
        if player in self.winners:
            self.winners.remove(player)

    def loop(self):
        while True:
            events = self.selector.select(timeout=None)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj)

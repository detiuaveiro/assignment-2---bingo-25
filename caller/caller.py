#!/bin/python
import base64
import selectors
import sys
import socket
import random
import fcntl
import os
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
        self.PLAYERS_SHUFFLE = {}                                               # Dictionary holding the symmetric key and shuffled deck of each Player
        self.player_counter = 0                                                 # Counts already registered Players
        self.winners = []                                                       # The determined winners
        self.playing_area_pk = None                                             # Playing Area Public Key
        self.game_finished = False                                              # Flag to determine if the game has finished

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
        try:
            message = (None, None)
            message = proto.Protocol.recv_msg(self.socket)
            msg = message[0]
            signature = message[1]
            certificate = message[2]
        except:
            msg, signature = message
            certificate = None

        if isinstance(msg, proto.Register_NACK):
            # Playing Area rejeitou Caller
            print("Register Rejected")
            print("Shutting down...")
            exit()
        elif isinstance(msg, proto.Register_ACK):
            self.playing_area_pk = msg.pk
            print("Register Accepted")


    def read_data(self, socket):
        """
        This function will determine the class of the received Message, and call the code that should be executed when an instance of this Message is received
        :param socket: The calling socket
        :return:
        """
        try:
            message = (None, None)
            message = proto.Protocol.recv_msg(socket)
            msg = message[0]
            signature = message[1]
            certificate = message[2]
        except Exception as e:
            print(e)
            msg, signature = message
            certificate = None

        # Verify if the signature of the message belongs to the Playing Area
        if signature is not None:
            sender_ID = msg.ID
            if sender_ID is None:
                sender_pub_key = self.playing_area_pk
            else:
                sender_pub_key = self.PLAYERS[sender_ID]["pk"]

            if not secure.verify_signature(msg, signature, sender_pub_key):
                if sender_ID is None:
                    # If the Playing Area signature is faked, the game is compromised
                    print("The Playing Area signature was forged! The game is compromised.")
                    print("Shutting down...")
                    self.selector.unregister(socket)
                    socket.close()
                    exit()
                else:
                    self.disqualify_player(sender_ID)

        reply = None

        if isinstance(msg, proto.RegisterMessage):
            # REGISTER MESSAGE WITH PLAYER INFORMATION
            self.player_counter += 1
            self.PLAYERS[self.player_counter] = {"nick": msg.nick, "pk": msg.pk}
            self.PLAYERS_SHUFFLE[self.player_counter] = {"deck": None, "sym_key": None}

            print(f"Registered Player {self.player_counter} with nick {msg.nick}")
            if self.player_counter == self.number_of_players:
                # Atingido limite de jogadores: Mandar mensagem BEGIN GAME para a Playing Area
                print("The limit of available players has been reached. I will now start the game.")

                # Create the Begin Game Message
                users = {}
                # Get caller public key
                users[0] = self.public_key
                # Add the other players public keys
                users = {**users, **{user_id: self.PLAYERS[user_id]["pk"] for user_id in self.PLAYERS.keys()}}
                msg = proto.Begin_Game(self.ID, users)
                signature = secure.sign_message(msg, self.private_key)
                reply = proto.SignedMessage(msg, signature)

                proto.Protocol.send_msg(socket, reply)

                # Gerar o deck e criar a mensagem para enviá-lo
                reply = self.generate_deck()
                print("Generated the Deck")
        elif isinstance(msg, proto.Commit_Card):
            self.PLAYERS[msg.ID]["card"] = msg.card
            self.PLAYERS[msg.ID]["cheated"] = False
            self.PLAYERS_SHUFFLE[msg.ID]["deck"] = msg.deck
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
                if not msg.cheaters[player] and int(player) in self.PLAYERS:
                    self.PLAYERS[int(player)]["cheated"] = True

            # If a player has cheated, disqualify them
            cheaters = []

            for player in self.PLAYERS:
                if self.PLAYERS[int(player)]["cheated"]:
                    cheaters.append(int(player))

            for player in set(cheaters):
                self.disqualify_player(int(player))

            if msg.stage == "Cards":
                print("Verification process completed")

                # Start Deck Validation Process
                print("\nStep 3")
                info = {}
                info[0] = {"deck": self.initial_deck, "sym_key": self.sym_key}
                for player in self.PLAYERS_SHUFFLE.keys():
                    info[player] = {"deck": self.PLAYERS_SHUFFLE[int(player)]["deck"],
                                    "sym_key": self.PLAYERS_SHUFFLE[int(player)]["sym_key"]}

                reply = proto.Post_Final_Decks(self.ID, info, self.signed_final_deck)

                print("I will now start to decrypt the Deck and verify if anyone cheated")
                self.decrypt(info)
            else:
                print("Deck Validation completed")

                if len(cheaters) > 0:
                    print("Shuffling process was compromised. This game can no longer go on.")
                    self.selector.unregister(socket)
                    socket.close()
                    print('Shutting down...')
                    exit()
                reply = proto.Ask_For_Winner(self.ID)
                self.find_winner()
        elif isinstance(msg, proto.Post_Sym_Keys):
            # Symmetric keys of all Players in the games
            print("Received the symmetric keys of the Players")
            for player in msg.sym_key.keys():
                self.PLAYERS_SHUFFLE[int(player)]["sym_key"] = msg.sym_key[player]
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
                if (len(self.winners) > 0):
                    print("Congratulations!")
                else:
                    print("There are no winners, only cheaters")
                self.game_finished = True
                reply = proto.Winner_ACK(self.ID, self.winners)    
        elif isinstance(msg, proto.Ask_Sym_Keys):
            sk = base64.b64encode(self.sym_key).decode()
            reply = proto.Post_Sym_Keys(self.ID, sk)
        elif isinstance(msg, proto.Disqualify):
            # The PA as warned the Caller that someone forged a signature
            print(f"Player {msg.disqualified_ID} has forged a signature. They are now disqualified")
            self.disqualify_player(int(msg.disqualified_ID))
        elif isinstance(msg, proto.Players_List):
            print("\nThe list of players is:")
            for player in msg.players:
                print(f"\n-> Player #{player}")
                print(f"   Nick: {msg.players[player]['nick']}")
                print(f"   Playing Card: {msg.players[player]['playing_card']}")
                print(f"   Public Key: {msg.players[player]['public_key']}")
                if msg.players[player]["disqualified"]:
                    print("   [DISQUALIFIED]")
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

        # We start the decryption process by taking the Deck encrypted by the player with the highest ID, and working all the way down to the lowest ID
        for i in range(len(keys)):
            if i != 0:
                # If there's a difference between the deck received in this step, and the deck determined after decryption in the previous step, the previous player cheated
                # The only being compared is if the set of numbers in both decks are matching - order doesn't matter
                dif = set(current_deck).difference(set([base64.b64decode(number) for number in decks[keys[i]]["deck"]]))

                if len(dif) > 0 and keys[i-1] in self.PLAYERS:
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
        if self.PLAYERS == {}: # If there are no more players in the game, end it
            print("\nThere are no more players in the game. I will now end it.")
            self.selector.unregister(self.socket)
            self.socket.close()
            exit()

        # If the player is in the winners list, take them off
        if player in self.winners:
            self.winners.remove(player)

    def got_keyboard_data(self, stdin):
        txt = stdin.read().strip()
        
        if txt == "1":
            msg = proto.Get_Players_List(self.ID)
            signature = secure.sign_message(msg, self.private_key)
            reply = proto.SignedMessage(msg, signature)
            proto.Protocol.send_msg(self.socket, reply)
        elif txt == "2":
            f = open("security.log", "r")
            content = f.read()
            print(content)
            f.close()
        elif txt == "3":
            print("Shutting down...")
            self.selector.unregister(self.socket)
            self.socket.close()
            exit()
        else:
            print("Invalid option") 
            

    def loop(self):
        # set sys.stdin non-blocking
        orig_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)
        # register events input from keyboard + socket messages
        self.selector.register(sys.stdin, selectors.EVENT_READ, self.got_keyboard_data)
        while True:
            if self.game_finished:
                sys.stdout.write("\nSelect one of the next options:\n")
                sys.stdout.write("1 - Get Players List\n")
                sys.stdout.write("2 - Get Audit Log\n")
                sys.stdout.write("3 - Exit\n")
                sys.stdout.write("Option: ")
                sys.stdout.flush()

            events = self.selector.select(timeout=None)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj)

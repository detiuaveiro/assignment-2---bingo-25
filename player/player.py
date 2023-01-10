#!/bin/python
import base64
import selectors
import sys
import socket
import random
import os
import fcntl
from pathlib import Path
from cryptography.hazmat.primitives import serialization

path_root = Path(__file__).parents[1]
sys.path.append(str(path_root))

import messages.protocol as proto
import security.security as secure
import security.vsc_security as vsc

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
        self.game_finished = False                                              # Flag to indicate if the game has finished
        self.users = {}                                                         # Dictionary with the users' IDs and PKs

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
        #print(f"Received: {msg} with signature {signature}")

        if isinstance(msg, proto.Register_NACK):
            # Playing Area rejeitou Player
            print("Register Rejected")
            print("Shutting down...")
            exit()
        elif isinstance(msg, proto.Register_ACK):
            self.playing_area_pk = msg.pk
            self.ID = msg.ID
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
        except:
            msg, signature = message
            certificate = None


        # Verify if the signature of the message belongs to the Playing Area
        if signature is not None:
            sender_ID = msg.ID
            if sender_ID is None:
                sender_pub_key = self.playing_area_pk
            else:
                sender_pub_key = self.users[sender_ID]
            if not secure.verify_signature(msg, signature, sender_pub_key):
                # If the Playing Area signature is faked, the game is compromised
                print("The Playing Area or the Caller signature was forged! The game is compromised.")
                print("Shutting down...")
                self.selector.unregister(socket)
                socket.close()
                exit()

        reply = None

        # Depending on the type of Message received, decide what to do
        if isinstance(msg, proto.Begin_Game):
            print("\nThe game is starting...")
            self.users = {int(k): v for k, v in msg.pks.items()}
        elif isinstance(msg, proto.Message_Deck):
            self.N = len(msg.deck)

            print("\nStep 1")
            print("I am shuffling the deck...")
            shuffled_deck = self.shuffle_deck(msg.deck)

            ''' implementation of one of the cheating systems'''
            rand = random.randint(0, 100)
            if rand>10:
                self.generate_playing_card()
                print("I have generated my Playing Card...")
            else:
                self.generate_cheating_card(shuffled_deck)
                print("I have generated my Cheating Playing Card...")

                cheat_message = proto.Cheat(self.ID)
                signature = secure.sign_message(cheat_message, self.private_key)
                new_message = proto.SignedMessage(cheat_message, signature)
                proto.Protocol.send_msg(socket, new_message)

            reply = proto.Commit_Card(self.ID, shuffled_deck, self.card)
        elif isinstance(msg, proto.Ask_Sym_Keys):
            print("Sending my symmetric key...")
            sk = base64.b64encode(self.sym_key).decode()
            reply = proto.Post_Sym_Keys(self.ID, sk)
        elif isinstance(msg, proto.Verify_Cards):
            # Initiate Playing Cards verification process
            reply = self.verify_cards(msg)
        elif isinstance(msg, proto.Disqualify):
            # Someone has been disqualified
            if int(msg.disqualified_ID) == int(self.ID):
                # I have been disqualified
                self.selector.unregister(socket)
                socket.close()
                print('I have been disqualified. Exiting...')
                exit()
            else:
                # Someone else was disqualified
                print(f"Player {msg.disqualified_ID} has been disqualified.")
                self.players_info.pop(int(msg.disqualified_ID))
        elif isinstance(msg, proto.Post_Final_Decks):
            reply = self.decrypt(msg.decks)
        elif isinstance(msg, proto.Ask_For_Winner):
            reply = self.find_winner()
        elif isinstance(msg, proto.Winner_ACK):
            if self.ID in [int(id) for id in msg.ID_winner]:
                print("\nBingo! I'm the Winner!")
            else:
                for person in msg.ID_winner:
                    print(f"\nCongratulations {person} for winning the game!")

            self.game_finished = True
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
            print('\nConnection to Playing Area lost, exiting...')
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
        self.private_key, self.public_key = secure.gen_assymetric_key()

    def shuffle_deck(self, deck):
        """
        Function responsible for the shuffling of the Playing Deck.
        Cheating can occur here.
        :return:
        """
        self.sym_key = secure.gen_symmetric_key()
        rand = random.randint(0, 100)
        if rand>5:
            new_deck = []
            for number in deck:
                new_deck.append(base64.b64encode(secure.encrypt_number(base64.b64decode(number), self.sym_key)).decode('utf-8'))

            return random.sample(new_deck, len(deck))
        else:
            #I am cheating -> send cheating message
            proto.Protocol.send_msg(self.socket, proto.Cheat(self.ID))
            print("I have cheated when shuffling the deck.")
            return self.card + random.sample(deck, len(deck)-len(self.card))
        

    def generate_playing_card(self):
        """
        Function responsible for the generation of the Playing Deck
        :return:
        """
        self.card = random.sample(list(range(1, self.N + 1)), int(self.N/4))

    def generate_cheating_card(self, deck):
        '''creating a smaller deck where it consists of the first value of the deck repeated several times'''
        print("I have cheated while generating my playing card")
        self.card = random.sample(deck[0], int(self.N/8))

    def verify_cards(self, msg):
        print("\nStep 2")
        print("Starting the process of validating Playing Cards...")
        cheaters = []

        for player in msg.playing_cards.keys():
            if int(player) == self.ID:
                continue

            print(f"Verifying Player {player}'s Playing Card...")

            if len(set(msg.playing_cards[player])) != int(self.N/4):
                print(f"Player {player} has cheated!")
                cheaters.append(player)
            else:
                print("Everything OK!")

            self.players_info[int(player)] = {"card": msg.playing_cards[player]}

        if len(cheaters) > 0:
            return proto.Verify_Card_NOK(self.ID, cheaters)
        else:
            print("Nobody has cheated")
            return proto.Verify_Card_OK(self.ID)

    def decrypt(self, decks):
        print("\nStep 3")
        print("I will now start to decrypt the Deck and verify if anyone cheated")
        keys = sorted(decks, reverse=True)
        current_deck = list()
        cheaters = []

        # We start the decryption process by taking the Deck encrypted by the player with the highest ID, and working all the way down to the lowest ID
        for i in range(len(keys)):
            if i != 0:
                # If there's a difference between the deck received in this step, and the deck determined after decryption in the previous step, the previous player cheated
                # The only being compared is if the set of numbers in both decks are matching - order doesn't matter
                dif = set(current_deck).difference(set([base64.b64decode(number) for number in decks[keys[i]]["deck"]]))

                if len(dif) > 0 and keys[i-1] != self.ID:
                    cheaters.append(keys[i-1])
                    print(f"Player {keys[i - 1]} cheated!")

            new_deck = list()
            for number in decks[keys[i]]["deck"]:
                flag = 1 if int(keys[i]) == 0 else 0
                decrypted_number = secure.decrypt_number(base64.b64decode(number), base64.b64decode(decks[keys[i]]["sym_key"]), flag)
                new_deck.append(decrypted_number)

            # The new current_deck will be the deck resulting from the decryption of the deck signed by the current player being analysed
            current_deck = new_deck

        print("Final plaintext Deck: " + str(current_deck))

        # The playing deck is the plaintext deck obtained at the end of the decryption process
        # self.playing_deck = current_deck
        self.playing_deck = current_deck

        if len(cheaters) > 0:
            return proto.Verify_Deck_NOK(self.ID, cheaters)
        else:
            print("Nobody has cheated")
            return proto.Verify_Deck_OK(self.ID)

    def find_winner(self):
        print("\nStep 4")
        print("\nI will now start the process of determining the winner:")
        print("This is my Playing card: " + str(self.card))

        winners = []

        # Find the Winner
        for number in self.playing_deck:
            if number in self.card:
                self.card.remove(number)

            if len(self.card) == 0:
                winners.append(self.ID)

            for player in self.players_info.keys():
                if number in self.players_info[player]["card"]:
                    self.players_info[player]["card"].remove(number)

                if len(self.players_info[player]["card"]) == 0:
                    winners.append(player)

            if len(winners) != 0:
                break

        if self.ID not in winners:
            # Maybe I will cheat
            rand = random.randint(0, 100)

            if rand < 5:
                #I am the cheater -> inside 10% chance
                print("I am cheating... inside the find winner function")
                proto.Protocol.send_msg(self.socket, proto.Cheat(self.ID))
                winners.append(self.ID)

        for person in winners:
            print(f"I determined {person} as a winner")
        return proto.Winner(self.ID, winners)

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

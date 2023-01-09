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
        msg, signature = proto.Protocol.recv_msg(self.socket)
        #print(f"Received: {msg} with signature {signature}")

        if isinstance(msg, proto.Register_NACK):
            # Playing Area rejeitou Player
            print("Register Rejected")
            print("Shutting down...")
            exit()
        elif isinstance(msg, proto.Register_ACK):
            self.ID = int(msg.ID)
            self.playing_area_pk = msg.pk
            print("Register Accepted")

    def read_data(self, socket):
        """
        This function will determine the class of the received Message, and call the code that should be executed when an instance of this Message is received
        :param socket: The calling socket
        :return:
        """
        msg, signature = proto.Protocol.recv_msg(socket)
        #print(f"Received: {msg}")

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

        # Depending on the type of Message received, decide what to do
        if isinstance(msg, proto.Begin_Game):
            print("\nThe game is starting...")
        elif isinstance(msg, proto.Message_Deck):
            self.N = len(msg.deck)

            print("\nStep 1")
            print("I am shuffling the deck...")
            shuffled_deck = self.shuffle_deck(msg.deck)
            print("I have generated my Playing Card...")

            ''' implementation of one of the cheating systems'''
            rand = random.randint(0, 100)
            if rand>10:
                self.generate_playing_card()
            else:
                self.generate_cheating_card(shuffled_deck)

                #ADAPTAR DEPOIS AO PROTOCOLO E VARIAVEIS DEFINIDAS - TODO!!!!!!!!
                cheat_message = proto.Cheat(self.ID)
                signature = secure.sign_message(cheat_message, self.private_key)
                new_message = proto.SignedMessage(cheat_message, signature)
                proto.Protocol.send_msg(socket, new_message)

            reply = proto.Commit_Card(self.ID, shuffled_deck, self.card)
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
        elif isinstance(msg, proto.Ask_Sym_Keys):
            print("Sending my symmetric key...")
            sk = base64.b64encode(self.sym_key).decode()
            reply = proto.Post_Sym_Keys(self.ID, sk)
        elif isinstance(msg, proto.Post_Final_Decks):
            reply = self.decrypt(msg.decks, msg.signed_deck)
        elif isinstance(msg, proto.Ask_For_Winner):
            reply = self.find_winner()
        elif isinstance(msg, proto.Winner_ACK):
            if self.ID in [int(id) for id in msg.ID_winner]:
                print("\nBingo! I'm the Winner!")
            else:
                for person in msg.ID_winner:
                    print(f"\nCongratulations {person} for winning the game!")
            self.selector.unregister(socket)
            socket.close()
            exit()
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
        self.private_key, self.public_key = secure.gen_assymetric_key()

    def shuffle_deck(self, deck):
        """
        Function responsible for the shuffling of the Playing Deck.
        Cheating can occur here.
        :return:
        """
        self.sym_key = secure.gen_symmetric_key()
        rand = random.randint(0, 100)
        if rand>10:
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

            #TODO: Verificar assinatura
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

    def decrypt(self, decks, signed_deck):
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

                if len(dif) > 0 and keys[i-1 != self.ID]:
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

        rand = random.randint(0, 100)

        if rand>5:
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
        else:
            #I am the cheater -> inside 10% chance
            print("I am cheating... inside the find winner function")
            proto.Protocol.send_msg(self.socket, proto.Cheat(self.ID))
            winners.append(self.ID)

        for person in winners:
            print(f"I determined {person} as a winner")
        return proto.Winner(self.ID, winners)

    def loop(self):
        while True:
            events = self.selector.select(timeout=None)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj)

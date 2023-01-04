#!/bin/python
import selectors
import sys
import socket
import json
from pathlib import Path

path_root = Path(__file__).parents[1]
sys.path.append(str(path_root))

from messages.messages import send_msg, recv_msg


class Player:
    ADDRESS = '127.0.0.1'

    def __init__(self, nick: str, port):
        self.nick = nick

        # Criação da Socket e do Selector
        self.selector = selectors.DefaultSelector()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.port = port
        self.N = 0

    def connect(self):
        """
                Function used to connect the created Socket to the Playing Area. The port passed in the command-line as an argument to this script should be the port where the Playing Area runs.
                """
        # Conexão à socket da Playing Area
        self.socket.connect((self.ADDRESS, self.port))
        self.selector.register(self.socket, selectors.EVENT_READ, self.read_data)

        # Envio da Register Message à Playing Area
        message = {'class': 'Register', 'type': 'Player', 'nick': self.nick}
        send_msg(self.socket, json.dumps(message).encode('UTF-8'))

        # Verificação da resposta recebida
        msg = recv_msg(self.socket)
        if msg == None:
            print("None")
        if msg['class'] == "Register NACK":
            # Playing Area rejeitou Player
            print("Register Rejected")
            print("Shutting down...")
            exit()

        # Se o registo foi bem sucedido, gerar par de chaves assimétricas
        self.generate_keys()

    def generate_keys(self):
        """
        Function responsible for the generation of this User's assymetric key pair
        :return:
        """
        pass

    def read_data(self, socket):
        """
        This function will determine the class of the received Message, and call the code that should be executed when an instance of this Message is received
        :param socket: The calling socket
        :return:
        """
        msg = recv_msg(socket)

        if msg == None:
            self.selector.unregister(socket)
            socket.close()
            print('Connection to Playing Area lost')
            exit()
        elif msg['class'] == "BEGIN_GAME":
            # Fazer forward da Mensagem para todos os jogadores
            self.N = msg['N']

    def loop(self):
        while True:
            events = self.selector.select(timeout=None)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj)

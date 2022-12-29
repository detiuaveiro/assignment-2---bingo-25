#!/bin/python
import selectors
import sys
import socket
import json
from messages import send_msg, exact_recv, recv_msg


class Caller:
    ADDRESS = '127.0.0.1'

    def __init__(self, nick: str, port):
        self.nick = nick

        # Criação da Socket e do Selector
        self.selector = selectors.DefaultSelector()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.port = port

    def connect(self):
        """
        Function used to connect the created Socket to the Playing Area. The port passed in the command-line as an argument to this script should be the port where the Playing Area runs.
        """
        # Conexão à socket da Playing Area
        self.socket.connect( self.ADDRESS, self.port)
        self.selector.register(self.socket, selectors.EVENT_READ, self.read_data)

        # Envio da Register Message à Playing Area
        message = {'class': 'Register', 'type': 'Caller', 'nick': self.nick}
        send_msg(self.socket, json.dumps(message).encode('UTF-8'))

        # Verificação da resposta recebida
        msg = recv_msg(self.socket)
        if msg == None:
            print("None")
        if msg['class'] == "Register NACK":
            # Playing Area rejeitou Caller
            print("Register Rejected")
            print("Shutting down...")
            exit()

    def read_data(self, socket):
        """
        This function will determine the class of the received Message, and call the code that should be executed when an instance of this Message is received
        :param socket: The calling socket
        :return:
        """

    def loop(self):
        while True:
            events = self.selector.select(timeout=None)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj)

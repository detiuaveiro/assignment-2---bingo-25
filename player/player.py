#!/bin/python
import selectors
import sys
import socket
import json
from messages import send_msg, exact_recv, recv_msg


class Player:
    ADDRESS = '127.0.0.1'

    def __init__(self, nick: str, port):
        self.nick = nick

        self.selector = selectors.DefaultSelector()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.port = port

    def connect(self):
        self.socket.connect(self.ADDRESS, self.port)

        self.selector.register(self.socket, selectors.EVENT_READ, data=None)

        message = {'class': 'Register', 'type': 'Player', 'nick': self.nick}
        send_msg(self.socket, json.dumps(message).encode('UTF-8'))

        data = recv_msg(self.socket)
        if data == None:
            print("None")

        print(data)

    def loop(self):
        while True:
            events = self.selector.select(timeout=None)
            for key, mask in events:
                print("Livin la vida loca")

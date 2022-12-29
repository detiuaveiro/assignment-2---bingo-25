#!/bin/python
import selectors
import sys
import socket
import json
from messages import send_msg, exact_recv, recv_msg


class Caller:
    ADDRESS = '127.0.0.1'

    def __init__(self, nick: str, port, N = 60, players = 4):
        self.nick = nick

        # Criação da Socket e do Selector
        self.selector = selectors.DefaultSelector()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.port = port
        self.number_of_players = players
        self.PLAYERS = {}
        self.player_counter = 0
        self.N = N                                                              # Números a considerar na geração do Playing Deck

    def connect(self):
        """
        Function used to connect the created Socket to the Playing Area. The port passed in the command-line as an argument to this script should be the port where the Playing Area runs.
        """
        # Conexão à socket da Playing Area
        self.socket.connect( self.ADDRESS, self.port)
        self.selector.register(self.socket, selectors.EVENT_READ, self.read_data)

        # Envio da Register Message à Playing Area
        message = {'class': 'Register', 'type': 'Caller', 'nick': self.nick, 'number_of_players': self.number_of_players}
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
        '''
            CÓDIGO A SER USADO APÓIS IMPLEMENTAÇÃO DO PROTOCOLO DE MENSAGENS
                if isinstance(msg, ProtoBadFormat): # Socket closed
                    selector.unregister( key.fileobj )
                    key.fileobj.close()
                    print( 'Client removed' )
                    continue
                elif isinstance(msg, RegisterMessage):
                    pass 
            '''

        ''' CÓDIGO USADO PARA TESTE ENQUANTO PROTOCOLO DE MENSAGENS NÃO FOR IMPLEMENTADO '''
        msg = recv_msg(socket)

        if msg == None:
            self.selector.unregister(socket)
            socket.close()
            print('Connection to Playing Area lost')
            exit()

        if msg['class'] == "Register":
            # REGISTER MESSAGE WITH PLAYER INFORMATION
            self.player_counter += 1
            self.PLAYERS[self.player_counter] = {"nick": msg['nick']}
            if self.player_counter == self.number_of_players:
                # Atingido limite de jogadores: Mandar mensagem BEGIN GAME para a Playing Area

                message = {'class': 'BEGIN_GAME', 'N': self.N}
                send_msg(socket, message)


        if reply != None:
            reply = json.dumps(reply)
            reply = reply.encode('UTF-8')
            send_msg(socket, reply)

    def loop(self):
        while True:
            events = self.selector.select(timeout=None)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj)

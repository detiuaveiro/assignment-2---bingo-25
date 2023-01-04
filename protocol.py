import json 
from socket import socket
from datetime import datetime

class Message:
    """Message Type."""
    def __init__(self, command):
        self.command = command
    
class JoinMessage(Message):
    """Message to join a chat channel."""
    def __init__(self, channel):
        self.channel = channel
        super().__init__("join")

    def __repr__(self):
        dicionario = {"command":"join", "channel": self.channel}
        return json.dumps(dicionario)

class RegisterMessage(Message):
    """Message to register username in the server."""
    def __init__(self, user):
        self.user = user
        super().__init__("register")

    def __repr__(self):
        return json.dumps({"command": "register", "user" :self.user})

    
class TextMessage(Message):
    """Message to chat with other clients."""
    def __init__(self, message, channel, ts):
        self.message = message
        self.channel = channel
        self.ts = ts
        super().__init__("message")
        
    def __repr__(self):
        if self.channel is None:
            dicionario = {"command":"message", "message": self.message, "ts":self.ts}
        else:
            dicionario = {"command":"message", "message": self.message, "channel":self.channel ,"ts": self.ts}
        return json.dumps(dicionario)

        
class Protocol:

    @classmethod
    def register(cls, username: str) -> RegisterMessage:
        """Creates a RegisterMessage object."""
        obj1 = RegisterMessage(username)
        return obj1


    @classmethod
    def join(cls, channel: str) -> JoinMessage:
        """Creates a JoinMessage object."""
        obj2 = JoinMessage(channel)
        return obj2

    @classmethod
    def message(cls, message: str, channel: str = None) -> TextMessage:
        """Creates a TextMessage object."""
        ts = int(datetime.now().timestamp())
        obj3 = TextMessage(message, channel, ts)
        return obj3

    @classmethod
    def send_msg(cls, connection: socket, msg: Message):
        """Sends through a connection a Message object."""
        #connection e uma socket -> depende do channel e do user maybe
        if msg.command == "register":
            dicionario = {"command": "register", "user" : msg.user}
        if msg.command == "join":
            dicionario = {"command":"join", "channel": msg.channel}
        if msg.command == "message":
            if msg.channel is None:
                dicionario = {"command":"message", "message": msg.message, "ts": msg.ts}
            else:
                dicionario = {"command":"message", "message": msg.message, "channel":msg.channel ,"ts": msg.ts}

        size = len(json.dumps(dicionario))
        connection.send(size.to_bytes(2, "big"))
        connection.send(json.dumps(dicionario).encode('UTF-8'))

    @classmethod
    def recv_msg(cls, connection: socket) -> Message:
        """Receives through a connection a Message object."""
        data = connection.recv(2)           #recebe os primeiros 2 bytes
        #print(data)

        if not data:
            return None

        tam = int.from_bytes(data, "big")
        data = connection.recv(tam)

        #data e os bytes da mensagem que recebemos em json

        #verificar que tem mensagem:
        try:
            # carregar o json para um dicionario
            dicionario = json.loads(data.decode('UTF-8'))
        except:
            raise BadFormatError(data)

        #verificar q cumpre os requesitos:

        #verificar q o elemento command existe
        try:
            value = dicionario["command"]
        except:
            raise BadFormatError(data)

        if value == "register":
            try:
                msg = Protocol.register(dicionario["user"])
            except:
                raise BadFormatError(data)

        elif value == "join":
            try:
                msg = Protocol.join(dicionario["channel"])
            except:
                raise BadFormatError(data)

        elif value == "message":
            try:
                if "channel" not in dicionario:
                    msg = Protocol.message(dicionario["message"], None)
                else:
                    msg = Protocol.message(dicionario["message"], dicionario["channel"])
            except:
                raise BadFormatError(data)

        else:
            raise BadFormatError(data)

        return msg


class BadFormatError(Exception):
    """Exception when source message is not in the Protocol."""

    def __init__(self, original_msg: bytes=None) :
        """Store original message that triggered exception."""
        self._original = original_msg

    @property
    def original_msg(self) -> str:
        """Retrieve original message as a string."""
        return self._original.decode("utf-8")

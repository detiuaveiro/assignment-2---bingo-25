import json 
from socket import socket
from datetime import datetime

class Message:
    """Message Type."""
    def __init__(self, command):
        self.command = command

class RegisterMessage(Message):
    """Message to register username in the server."""
    def __init__(self, type, nick, pk, ass_cc, nplayers):
        self.type = type
        self.user = nick
        self.pk = pk
        self.ass_cc = ass_cc
        self.nplayers = nplayers
        super().__init__("Register")

    def __repr__(self):
        if self.type == "Caller":
            return json.dumps({"command": self.command, "type": self.type, "number_of_players": self.nplayers})   #caller does not have a nick 
        if self.type == "Player":
            return json.dumps({"command": self.command, "type": self.type, "nick": self.nick, "number_of_players": self.nplayers})
    
class Register_ACK(Message):
    def __init__(self, ok, userID):
        self.ok = ok
        self.userID = userID
        super().__init__("Register_ACK")

    def __repr__(self):
        return json.dumps({"command": self.command, "ok": self.ok, "userID": self.userID})

class Begin_Game(Message):
    def __init__(self, pks):
        self.pks = pks
        super().__init__("Begin_Game")
    
    def __repr__(self):
        return json.dumps({"command": self.command, "pks": self.pks})
    pass


class Message_Deck(Message):
    def __init__(self, deck):
        self.deck = deck
        super().__init__("Message_Deck")

    def __repr__(self):
        return json.dumps({"command": self.command, "deck": self.deck})

class Commit_Card(Message):
    def __init__(self, deck, card):
        self.deck = deck
        self.card = card
        super().__init__("Commit_Card")
    
    def __repr__(self):
        return json.dumps({"command": self.command, "deck": self.deck, "playing_card": self.card})


class Sign_Final_Deck_ACK(Message):
    """Message to chat with other clients."""
    def __init__(self, deck):
        self.deck = deck
        super().__init__("Sign_Final_Deck")

    def __repr__(self):
        return json.dumps({"command": self.command, "deck": self.deck})


#Verificação das playing cards ---------------------------------------------------

class Verify_Card(Message):
    def __init__(self, id_user, playing_card):
        self.id_user = id_user
        self.playing_card = playing_card
        super().__init__("Verify_Card")

    def __repr__(self):
        return json.dumps({"command": self.command, "id_user": self.id_user, "playing_card": self.playing_card})

class Verify_Card_OK(Message):
    def __init__(self):
        super().__init__("Verify_Card_OK")
    def __repr__(self):
        return json.dumps({"command": self.command})

class Verify_Card_NOK(Message):
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__("Verify_Card_NOK")
    def __repr__(self):
        return json.dumps({"command": self.command, "id_user": self.user_id})

class Disqualify(Message):
    def __init__(self, id_user):
        self.id_user = id_user
        super().__init__("Disqualify")
    def __repr__(self):
        return json.dumps({"command": self.command, "id_user": self.id_user})

class Cards_Validated(Message):
    def __init__(self):
        super().__init__("Cards_Validated")
    def __repr__(self):
        return json.dumps({"command": self.command})

# Validação do playing deck

class ASK_Sym_Keys(Message):
    def __init__(self):
        super().__init__("ASK_Sym_Keys")
    def __repr__(self):
        return json.dumps({"command": self.command})

class Post_Sym_Keys(Message):
    def __init__(self, id_user, sym_key):
        self.id_user = id_user
        self.sym_key = sym_key
        super().__init__("Post_Sym_Keys")
    def __repr__(self):
        return json.dumps({"command": self.command, "id_user": self.id_user, "sym_key": self.sym_key})

class Post_Final_Decks(Message):
    def __init__(self, decks, id, sym_key):
        self.decks = decks
        self.id = id
        self.sym_key = sym_key
        super().__init__("Post_Sym_Keys")
    def __repr__(self):
        return json.dumps({"command": self.command, "decks": self.decks, "id": self.id, "sym_key": self.sym_key})

class Verify_Deck_OK(Message):
    def __init__(self):
        super().__init__("Verify_Deck_OK")
    def __repr__(self):
        return json.dumps({"command": self.command})

class Verify_Deck_NOK(Message):
    def __init__(self):
        super().__init__("Verify_Deck_NOK")
    def __repr__(self):
        return json.dumps({"command": self.command})

# Determinar Vencedor:

class Ask_For_Winner(Message):
    def __init__(self, id_user):
        self.id_user = id_user
        super().__init__("Ask_For_Winner")
    def __repr__(self):
        return json.dumps({"command": self.command, "id_user": self.id_user})

class Winner(Message):
    def __init__(self, id_user):
        self.id_user = id_user
        super().__init__("Winner")
    def __repr__(self):
        return json.dumps({"command": self.command, "id_user": self.id_user})

class Winner_ACK(Message):
    def __init__(self, id_user):
        self.id_user = id_user
        super().__init__("Winner_ACK")
    def __repr__(self):
        return json.dumps({"command": self.command, "id_user": self.id_user})


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

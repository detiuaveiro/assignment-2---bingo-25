import json 
from socket import socket

class Message:
    """Message Type."""
    def __init__(self, command, signature, original_id=None):
        self.command = command
        self.original_id = original_id

class RegisterMessage(Message):
    """Message to register username in the server."""
    def __init__(self, original_id, type, pk = None, ass_cc = None, nick = None, num_players = None):
        self.type = type
        self.pk = pk
        self.ass_cc = ass_cc
        self.nick = nick
        self.num_players = num_players
        super().__init__("Register", original_id)

    def __repr__(self):
        if self.type == "Caller":
            return json.dumps({"command": self.command, "original_id": self.original_id, "nick": self.nick, "pk": self.pk, "ass_cc": self.ass_cc, "type": self.type, "num_players": self.num_players })
        if self.type == "Player":
            return json.dumps({"command": self.command, "original_id": self.original_id, "nick": self.nick, "pk": self.pk, "ass_cc": self.ass_cc, "type": self.type})


class Register_ACK(Message):
    def __init__(self, original_id, id):
        self.id = id
        self.original_id = original_id
        super().__init__("Register_ACK", original_id)

    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id, "id": self.id})

class Cheat(Message):
    def __init__(self, original_id, id_cheater):
        self.id_cheater = id_cheater
        super().__init__("Cheat", original_id)
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id, "id_cheater": self.id_cheater})

class Register_NACK(Message):
    def __init__(self, original_id):
        super().__init__("Register_NACK", original_id)

    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id})

class Begin_Game(Message):
    def __init__(self, original_id, pks=None):
        self.pks = pks
        super().__init__("Begin_Game", original_id)
    
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id, "pks": self.pks})
    pass

class Message_Deck(Message):
    def __init__(self, original_id, deck):
        self.deck = deck
        super().__init__("Message_Deck", original_id)

    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id, "deck": self.deck})

class Commit_Card(Message):
    def __init__(self, original_id, deck, card, id_user=None):
        self.deck = deck
        self.card = card
        self.id_user = id_user
        super().__init__("Commit_Card", original_id)
    
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id, "deck": self.deck, "card": self.card, "id_user": self.id_user})

class Sign_Final_Deck_ACK(Message):
    """Message to chat with other clients."""
    def __init__(self, original_id, playing_cards):
        self.playing_cards = playing_cards
        super().__init__("Sign_Final_Deck_ACK", original_id)

    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id, "playing_cards": self.playing_cards})

#Verificação das playing cards ---------------------------------------------------

class Verify_Cards(Message):
    def __init__(self, original_id, playing_cards):
        self.playing_cards = playing_cards
        super().__init__("Verify_Cards", original_id)

    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id, "playing_cards": self.playing_cards})

class Verify_Card_OK(Message):
    def __init__(self, signature, original_id):
        super().__init__("Verify_Card_OK", original_id,)
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id})

class Verify_Card_NOK(Message):
    def __init__(self, original_id, users):
        self.users = users
        super().__init__("Verify_Card_NOK", original_id)
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id, "users": self.users})

class Cheat_Verify(Message):
    def __init__(self, original_id, cheaters, stage):
        self.cheaters = cheaters
        self.stage = stage
        super().__init__("Cheat_Verify", original_id)
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id, "cheaters": self.cheaters, "stage": self.stage})

class Disqualify(Message):
    def __init__(self, original_id, id_user):
        self.id_user = id_user
        super().__init__("Disqualify", original_id)
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id, "id_user": self.id_user})

class Cards_Validated(Message):
    def __init__(self, original_id):
        super().__init__("Cards_Validated", original_id)
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id})

# Validação do playing deck ------------------------------------------------------

class Ask_Sym_Keys(Message):
    def __init__(self, original_id):
        super().__init__("Ask_Sym_Keys", original_id)
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id})

class Post_Sym_Keys(Message):
    def __init__(self, original_id, sym_key):
        self.sym_key = sym_key
        super().__init__("Post_Sym_Keys", original_id)
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id, "sym_key": self.sym_key})

class Post_Final_Decks(Message):
    def __init__(self, original_id, decks, signed_deck):
        self.decks = decks
        self.signed_deck = signed_deck
        super().__init__("Post_Final_Decks", original_id)
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id, "decks": self.decks, "signed_deck": self.signed_deck})

class Verify_Deck_OK(Message):
    def __init__(self, original_id):
        super().__init__("Verify_Deck_OK", original_id)
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id})

class Verify_Deck_NOK(Message):
    def __init__(self, original_id, users):
        super().__init__("Verify_Deck_NOK", original_id)
        self.users = users
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id, "users": self.users})

# Determinar Vencedor ------------------------------------------------------------

class Ask_For_Winner(Message):
    def __init__(self, original_id):
        super().__init__("Ask_For_Winner", original_id)
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id})

class Winner(Message):
    def __init__(self, original_id, id, id_winner):
        self.id = id
        self.id_winner = id_winner
        super().__init__("Winner", original_id)
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id, "id": self.id, "id_winner": self.id_winner})

class Winner_ACK(Message):
    def __init__(self, original_id, id_user):
        self.id_user = id_user
        super().__init__("Winner_ACK", original_id)
    def __repr__(self):
        return json.dumps({"command": self.command, "original_id": self.original_id, "id_user": self.id_user})

class Protocol:
    # Adaptar para as mensagens raw: 

    @classmethod
    def send_msg(cls, connection: socket, msg: Message):
        #connection e uma socket -> depende do channel e do user maybe
        dicionario = repr(msg)

        size = len(dicionario)
        connection.send(size.to_bytes(4, "big"))
        connection.send(dicionario.encode('UTF-8'))

    @classmethod
    def exact_recv(cls, src, length):
        data = bytearray(0)

        while len(data) != length:
            more_data = src.recv( length - len(data) )
            if len(more_data) == 0: # End-of-File
                return None
            data.extend( more_data )

        if data == None:  # Socket closed
            # Gerar uma Classe de Erro (CDProtoBadFormat)
            return BadFormatError("No data in exact_recv")
        return data

    @classmethod
    def recv_msg(cls, src) -> Message:
        """Receives through a connection a Message object."""
        data = Protocol.exact_recv(src, 4) # 4-byte integer, network byte order (Big Endian)

        if data == None:
            return None

        length = int.from_bytes(data, 'big')
        data = Protocol.exact_recv(src, length)

        # ver qual o tipo da mensagem
        msg = None

        try:
            dicionario = json.loads(data.decode('UTF-8'))
        except:
            raise BadFormatError(data)

        try:
            value = dicionario["command"]
        except:
            raise BadFormatError(data)

        if value == "Register":
            try:
                if dicionario["type"] == "Caller":
                    msg = RegisterMessage(dicionario["type"], dicionario["pk"], dicionario["ass_cc"], dicionario["nick"], dicionario["num_players"])
                elif dicionario["type"] == "Player":
                    msg = RegisterMessage(dicionario["type"], dicionario["pk"], dicionario["ass_cc"], dicionario["nick"])
            except:
                raise BadFormatError(data)
        
        if value == "Register_ACK":
            try:
                msg = Register_ACK(dicionario["id"])
            except:
                raise BadFormatError(data)

        if value == "Begin_Game":
            try:
                msg = Begin_Game(dicionario["pks"])
            except:
                raise BadFormatError(data)

        if value == "Message_Deck":
            try:
                msg = Message_Deck(dicionario["deck"])
            except:
                raise BadFormatError(data)

        if value == "Commit_Card":
            try:
                msg = Commit_Card(dicionario["deck"], dicionario["card"], dicionario["id_user"])
            except:
                raise BadFormatError(data)

        if value == "Sign_Final_Deck_ACK":
            try:
                msg = Sign_Final_Deck_ACK(dicionario["playing_cards"])
            except:
                raise BadFormatError(data)

        if value == "Verify_Cards":
            try:
                msg = Verify_Cards(dicionario["playing_cards"])
            except:
                raise BadFormatError(data)

        if value == "Verify_Card_OK":
            try:
                msg = Verify_Card_OK()
            except:
                raise BadFormatError(data)

        if value == "Verify_Card_NOK":
            try:
                msg = Verify_Card_NOK(dicionario["id_user"])
            except:
                raise BadFormatError(data)
        
        if value == "Cheat_Verify":
            try:
                msg = Cheat_Verify(dicionario["cheaters"], dicionario["stage"])
            except:
                raise BadFormatError(data)

        if value == "Disqualify":
            try:
                msg = Disqualify(dicionario["id_user"])
            except:
                raise BadFormatError(data)

        if value == "Cards_Validated":
            try:
                msg = Cards_Validated()
            except:
                raise BadFormatError(data)

        if value == "Ask_Sym_Keys":
            try:
                msg = Ask_Sym_Keys()
            except:
                raise BadFormatError(data)

        if value == "Post_Sym_Keys":
            try:
                msg = Post_Sym_Keys(dicionario["sym_key"])
            except:
                raise BadFormatError(data)

        if value == "Post_Final_Decks":
            try:
                msg = Post_Final_Decks(dicionario["decks"], dicionario["signed_deck"])
            except:
                raise BadFormatError(data)

        if value == "Verify_Deck_OK":
            try:
                msg = Verify_Deck_OK()
            except:
                raise BadFormatError(data)
        
        if value == "Verify_Deck_NOK":
            try:
                msg = Verify_Deck_NOK(dicionario["users"])
            except:
                raise BadFormatError(data)

        if value == "Ask_For_Winner":
            try:
                msg = Ask_For_Winner()
            except:
                raise BadFormatError(data)

        if value == "Winner":
            try:
                msg = Winner(dicionario["id"], dicionario["id_winner"])
            except:
                raise BadFormatError(data)

        if value == "Winner_ACK":
            try:
                msg = Winner_ACK(dicionario["id_user"])
            except:
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

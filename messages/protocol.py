import base64
import json 
from socket import socket

#Parent Message Classes ---------------------------------------------------
class SuperMessage:
    """Used in the definition of send and recv functions"""
    def __init__(self):
        pass

class Message(SuperMessage):
    """Message Type"""
    def __init__(self, command, ID=None):
        self.command = command
        self.ID = ID
        super().__init__()

class SignedMessage(SuperMessage):
    """Signed message"""
    def __init__(self, message, signature):
        self.message = message
        self.signature = signature
        super().__init__()

    def __repr__(self):
        data = self.message.to_json()
        return json.dumps({"message": data, "signature": self.signature})

class CertMessage(SignedMessage):
    """Message accompanied by a CC signature"""
    def __init__(self, message, signature, certificate):
        self.certificate = certificate
        super().__init__(message, signature)
    def __repr__(self):
        data = self.message.to_json()
        return json.dumps({"message": data, "signature": self.signature, "certificate": self.certificate})


#Register Messages ---------------------------------------------------
class RegisterMessage(Message):
    """Message to register username in the server."""
    def __init__(self, type, pk = None, ass_cc = None, nick = None, num_players = None):
        self.type = type
        self.pk = pk
        self.ass_cc = ass_cc
        self.nick = nick
        self.num_players = num_players
        super().__init__("Register")

    def __repr__(self):
        if self.type == "Caller":
            return json.dumps({"command": self.command, "ID": self.ID, "nick": self.nick, "pk": self.pk, "ass_cc": self.ass_cc, "type": self.type, "num_players": self.num_players })
        if self.type == "Player":
            return json.dumps({"command": self.command, "ID": self.ID, "nick": self.nick, "pk": self.pk, "ass_cc": self.ass_cc, "type": self.type})

    def to_json(self):
        if self.type == "Caller":
            return {"command": self.command, "ID": self.ID, "nick": self.nick, "pk": self.pk, "ass_cc": self.ass_cc, "type": self.type, "num_players": self.num_players }
        if self.type == "Player":
            return {"command": self.command, "ID": self.ID, "nick": self.nick, "pk": self.pk, "ass_cc": self.ass_cc, "type": self.type}


class Register_ACK(Message):
    def __init__(self, ID, pk):
        self.pk = pk
        super().__init__("Register_ACK", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID, "pk": self.pk})

    def to_json(self):
        return {"command": self.command, "ID": self.ID, "pk": self.pk}

class Cheat(Message):
    def __init__(self, ID):
        super().__init__("Cheat", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID})

    def to_json(self):
        return {"command": self.command, "ID": self.ID}

class Register_NACK(Message):
    def __init__(self):
        super().__init__("Register_NACK")

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID})

    def to_json(self):
        return {"command": self.command, "ID": self.ID}

class Begin_Game(Message):
    def __init__(self, ID, pks):
        self.pks = pks
        super().__init__("Begin_Game", ID)
    
    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID, "pks": self.pks})

    def to_json(self):
        return {"command": self.command, "ID": self.ID, "pks": self.pks}

class Message_Deck(Message):
    def __init__(self, ID, deck):
        self.deck = deck
        super().__init__("Message_Deck", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID, "deck": self.deck})
    
    def to_json(self):
        return {"command": self.command, "ID": self.ID, "deck": self.deck}

class Commit_Card(Message):
    def __init__(self, ID, deck, card):
        self.deck = deck
        self.card = card
        super().__init__("Commit_Card", ID)
    
    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID, "deck": self.deck, "card": self.card})

    def to_json(self):
        return {"command": self.command, "ID": self.ID, "deck": self.deck, "card": self.card}

class Sign_Final_Deck_ACK(Message):
    """Message to chat with other clients."""
    def __init__(self, ID, playing_cards):
        self.playing_cards = playing_cards
        super().__init__("Sign_Final_Deck_ACK", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID, "playing_cards": self.playing_cards})

    def to_json(self):
        return {"command": self.command, "ID": self.ID, "playing_cards": self.playing_cards}

#Verificação das playing cards ---------------------------------------------------

class Verify_Cards(Message):
    def __init__(self, ID, playing_cards):
        self.playing_cards = playing_cards
        super().__init__("Verify_Cards", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID, "playing_cards": self.playing_cards})
    
    def to_json(self):
        return {"command": self.command, "ID": self.ID, "playing_cards": self.playing_cards}

class Verify_Card_OK(Message):
    def __init__(self, ID):
        super().__init__("Verify_Card_OK", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID})

    def to_json(self):
        return {"command": self.command, "ID": self.ID}

class Verify_Card_NOK(Message):
    def __init__(self, ID, users):
        self.users = users
        super().__init__("Verify_Card_NOK", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID, "users": self.users})

    def to_json(self):
        return {"command": self.command, "ID": self.ID, "users": self.users}

class Cheat_Verify(Message):
    def __init__(self, cheaters, stage):
        self.cheaters = cheaters
        self.stage = stage
        super().__init__("Cheat_Verify")

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID, "cheaters": self.cheaters, "stage": self.stage})

    def to_json(self):
        return {"command": self.command, "ID": self.ID, "cheaters": self.cheaters, "stage": self.stage}

class Disqualify(Message):
    def __init__(self, disqualified_ID, ID=None):
        self.disqualified_ID = disqualified_ID
        super().__init__("Disqualify", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID, "disqualified_ID": self.disqualified_ID})

    def to_json(self):
        return {"command": self.command, "ID": self.ID, "disqualified_ID": self.disqualified_ID}

class Cards_Validated(Message):
    def __init__(self, ID):
        super().__init__("Cards_Validated", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID})

    def to_json(self):
        return {"command": self.command, "ID": self.ID}

# Validação do playing deck ------------------------------------------------------

class Ask_Sym_Keys(Message):
    def __init__(self):
        super().__init__("Ask_Sym_Keys")

    def __repr__(self):
        return json.dumps({"command": self.command})

    def to_json(self):
        return {"command": self.command}

class Post_Sym_Keys(Message):
    def __init__(self, ID, sym_key):
        self.sym_key = sym_key
        super().__init__("Post_Sym_Keys", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID, "sym_key": self.sym_key})

    def to_json(self):
        return {"command": self.command, "ID": self.ID, "sym_key": self.sym_key}

class Post_Final_Decks(Message):
    def __init__(self, ID, decks, signed_deck):
        self.decks = decks
        self.signed_deck = signed_deck
        super().__init__("Post_Final_Decks", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID, "decks": self.decks, "signed_deck": self.signed_deck})

    def to_json(self):
        return {"command": self.command, "ID": self.ID, "decks": self.decks, "signed_deck": self.signed_deck}

class Verify_Deck_OK(Message):
    def __init__(self, ID):
        super().__init__("Verify_Deck_OK", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID})

    def to_json(self):
        return {"command": self.command, "ID": self.ID}

class Verify_Deck_NOK(Message):
    def __init__(self, ID, users):
        super().__init__("Verify_Deck_NOK", ID)
        self.users = users

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID, "users": self.users})

    def to_json(self):
        return {"command": self.command, "ID": self.ID, "users": self.users}

# Determinar Vencedor ------------------------------------------------------------

class Ask_For_Winner(Message):
    def __init__(self, ID):
        super().__init__("Ask_For_Winner", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID})
    
    def to_json(self):
        return {"command": self.command, "ID": self.ID}

class Winner(Message):
    def __init__(self, ID, ID_winner):
        self.ID_winner = ID_winner
        super().__init__("Winner", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID, "ID_winner": self.ID_winner})

    def to_json(self):
        return {"command": self.command, "ID": self.ID, "ID_winner": self.ID_winner}

class Winner_ACK(Message):
    def __init__(self, ID, ID_winner):
        self.ID_winner = ID_winner
        super().__init__("Winner_ACK", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID, "ID_winner": self.ID_winner})

    def to_json(self):
        return {"command": self.command, "ID": self.ID, "ID_winner": self.ID_winner}

class Get_Players_List(Message):
    def __init__(self, ID):
        super().__init__("Get_Players_List", ID)

    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID})

    def to_json(self):
        return {"command": self.command, "ID": self.ID}

class Players_List(Message):
    def __init__(self, ID, players):
        self.players = players
        super().__init__("Players_List", ID)
    
    def __repr__(self):
        return json.dumps({"command": self.command, "ID": self.ID, "players": self.players})

    def to_json(self):
        return {"command": self.command, "ID": self.ID, "players": self.players}

class Protocol:
    # Adaptar para as mensagens raw: 

    @classmethod
    def send_msg(cls, connection: socket, msg: SuperMessage):
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
    def recv_msg(cls, src):
        """Receives through a connection a Message object."""
        isSigned = True
        isCertified = True
        signature = None

        # Get the length of the message
        data = Protocol.exact_recv(src, 4) # 4-byte integer, network byte order (Big Endian)

        if data == None:
            return None, None

        # Get the actual message, based on the length
        length = int.from_bytes(data, 'big')
        data = Protocol.exact_recv(src, length)

        # Check if message is SIgned or not
        msg = None
        certificate = None
        try:
            dicionario = json.loads(data.decode('UTF-8'))
        except:
            raise BadFormatError(data)
        
        try:
            ## Message is signed
            msg = dicionario["message"]
            signature = dicionario["signature"]
            try:
                ## Message comes with certificate
                certificate = dicionario["certificate"]
            except:
                ## Message does not come with certificate
                isCertified = False

            dicionario = msg                                            # So the code below can be reused without an if
        except:
            ## Message is not signed
            isSigned = False
        
        try:
            value = dicionario["command"]
        except:
            raise BadFormatError(data)


        # Check the type of the Message
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
                msg = Register_ACK(dicionario["ID"], dicionario["pk"])
            except:
                raise BadFormatError(data)

        if value == "Register_NACK":
            try:
                msg = Register_NACK()
            except:
                raise BadFormatError(data)

        if value == "Cheat":
            try:
                msg = Cheat(dicionario["ID"])
            except:
                raise BadFormatError(data)

        if value == "Begin_Game":
            try:
                msg = Begin_Game(dicionario["ID"], dicionario["pks"])
            except:
                raise BadFormatError(data)

        if value == "Message_Deck":
            try:
                msg = Message_Deck(dicionario["ID"], dicionario["deck"])
            except:
                raise BadFormatError(data)

        if value == "Commit_Card":
            try:
                msg = Commit_Card(dicionario["ID"], dicionario["deck"], dicionario["card"])
            except:
                raise BadFormatError(data)

        if value == "Sign_Final_Deck_ACK":
            try:
                msg = Sign_Final_Deck_ACK(dicionario["ID"], dicionario["playing_cards"])
            except:
                raise BadFormatError(data)

        if value == "Verify_Cards":
            try:
                msg = Verify_Cards(dicionario["ID"], dicionario["playing_cards"])
            except:
                raise BadFormatError(data)

        if value == "Verify_Card_OK":
            try:
                msg = Verify_Card_OK(dicionario["ID"])
            except:
                raise BadFormatError(data)

        if value == "Verify_Card_NOK":
            try:
                msg = Verify_Card_NOK(dicionario["ID"], dicionario["users"])
            except:
                raise BadFormatError(data)
        
        if value == "Cheat_Verify":
            try:
                msg = Cheat_Verify(dicionario["cheaters"], dicionario["stage"])
            except:
                raise BadFormatError(data)

        if value == "Disqualify":
            try:
                msg = Disqualify(dicionario["disqualified_ID"], dicionario["ID"])
            except:
                raise BadFormatError(data)

        if value == "Cards_Validated":
            try:
                msg = Cards_Validated(dicionario["ID"])
            except:
                raise BadFormatError(data)

        if value == "Ask_Sym_Keys":
            try:
                msg = Ask_Sym_Keys()
            except:
                raise BadFormatError(data)

        if value == "Post_Sym_Keys":
            try:
                msg = Post_Sym_Keys(dicionario["ID"], dicionario["sym_key"])
            except:
                raise BadFormatError(data)

        if value == "Post_Final_Decks":
            try:
                msg = Post_Final_Decks(dicionario["ID"], dicionario["decks"], dicionario["signed_deck"])
            except:
                raise BadFormatError(data)

        if value == "Verify_Deck_OK":
            try:
                msg = Verify_Deck_OK(dicionario["ID"])
            except:
                raise BadFormatError(data)
        
        if value == "Verify_Deck_NOK":
            try:
                msg = Verify_Deck_NOK(dicionario["ID"], dicionario["users"])
            except:
                raise BadFormatError(data)

        if value == "Ask_For_Winner":
            try:
                msg = Ask_For_Winner(dicionario["ID"])
            except:
                raise BadFormatError(data)

        if value == "Winner":
            try:
                msg = Winner(dicionario["ID"], dicionario["ID_winner"])
            except:
                raise BadFormatError(data)

        if value == "Winner_ACK":
            try:
                msg = Winner_ACK(dicionario["ID"], dicionario["ID_winner"])
            except:
                raise BadFormatError(data)
        
        if value == "Get_Players_List":
            try:
                msg = Get_Players_List(dicionario["ID"])
            except:
                raise BadFormatError(data)
        
        if value == "Players_List":
            try:
                msg = Players_List(dicionario["ID"], dicionario["players"])
            except:
                raise BadFormatError(data)
            

        return msg, signature, certificate
        

class BadFormatError(Exception):
    """Exception when source message is not in the Protocol."""

    def __init__(self, original_msg: bytes=None) :
        """Store original message that triggered exception."""
        self._original = original_msg

    @property
    def original_msg(self) -> str:
        """Retrieve original message as a string."""
        return self._original.decode("utf-8")

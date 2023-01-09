[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-c66648af7eb3fe8bc4f294546bfd86ef473780cde1dea487d3c4ff354943c9ae.svg)](https://classroom.github.com/online_ide?assignment_repo_id=9469158&assignment_repo_type=AssignmentRepo)

# Project 2 - Secure Game

## Project Description

This assignment will focus on the implementation of a robust protocol for handling a distributed game. The game under study will be Bingo, which is a game of chance. Implementation will consist of a server (caller) and multiple clients (players) communicating over a network (playing area).

## Authors

- Artur Correia (nº mec 102477)
- André Butuc (nº mec 103530)
- Bruna Simões (nº mec 103453)
- Daniel Carvalho (nº mec 77036)

## Message Protocol

In order to send different types of messages, a protocol was implemented in order to keep track of the different messages exchanged.

### Messages:

A in-depth documentation of the different messages implemented is as follows:

#### SuperMessage:
   
   Is the most primite type of message, and does not receive any parameters.

#### Message:

   Extends the SuperMessage class, and receives the parameters command and ID. The "command" field works as an identifier for the class type of different messages. It corresponds to exchanged messages' fundamental structure.

#### SignedMessage:

   Also extends the SuperMessage class, carries the normal message type and a signature, derived from the sender of the message.

#### CertMessage:

   Extends the SignedMessage class, which correspondes to a SignedMessage with an additional parameter, the certificate of the message.

#### RegisterMessage:

   Extends the Message class, and it's used to register an entity in the platform (a player or the caller). Has parameters such as type, public key, the citizen card signature and username.
   From the Message class, it inherits the command and ID parameters, command being "Register". 
   Depending on the type (Caller or Player), its json representation is different: the Caller has an aditional parameter, the number os players, which the Player doesn't have.


#### Register_ACK:

   Extends the Message class, with the additional parameter _pk_ which represents the public key. Its command field stores the type of the message, "Register_ACK".

#### Register_NACK:

   Is sent/received when a the RegisterMessage is not sucessful, and has no additional parameters.

#### Cheat:

   When players cheat, this message is sent in order to realise someone is cheating. However, its purpose is simply to let programmers know that someone has cheated, and no verifications will be made for this message in specific, since they are sent everytime a player cheats on purpose.
   Has no additional parameters.

#### Begin_Game:

   Message sent in order to start the game. Has an additional parameter the public keys of all players.

#### Message_Deck:

   Used to message the deck. Therefore, has an additional parameter, the deck, in order to be suffled by all players.

#### Commit_Card:

   Players send their card and their shuffled deck to the playing area. If it was the remaing player to shuffle the deck, it sinalizes the end of this process since all players have already shuffled the deck.

#### Sign_Final_Deck_ACK:

   Message to send the final deck, after being shuffled by all players. Therefore, the additional parameter is the final deck to be used in the game.

#### Verify_Cards:

   All player cards are sent to all players and the caller in order to verify that the card is not invalid and can be used in game, to prevent cheating.
   Therefore, has an additional parameter, playing_cards, that contains the cards of all players yet to be verified.

#### Verify_Card_OK:

   Sent when someone checks that the card (from another player) is legal and therefore is validated. Its a reply for the Verify_Cards message to confirm that the card sent can be used.
   Has no aditional parameters.

#### Verify_Card_NOK:

   Sent when certain users submit an invalid card. Has a parameter that contains a list of all players which card cannot be used in the game.

#### Ask_For_Winner:

   Sent by the caller in order to ask all players to determine a winner. Has no additional parameters.

#### Winner:

   Sent by each player, and contains a parameter ID_winner which is the winner determined by said players, that is, each player determines the winner, and sends this message with the id of the winner they think has won the game.
   Has the additional previously referenced parameter, ID_winner.

#### Winner_ACK:

   Sent by the caller after receiving all Winner messages from players, and determining itself based on these messages who the winner is. Proceeds to broadcast this message to all players in order to let them know the rightful winner. 
   Has the additional parameter, ID_winner which stores the id of the player that won the game.

#### Get_Players_List:

   Sent by a player to request a list of all players connected to the playing area. 
   Has no additional parameters.

#### Players_List:

   Sent as a reply of the message Get_Players_List, and delivers the list of all connected players to the playing area.
   Has an additional paramter, players, which stores all players connected and corresponds to the inquired information.

### Protocol:

The protocol has 3 different functions used to receive a message (recv_msg), send a message (send_msg). The last function (exact_recv) is determine all important contents of the message, which don't include the length of the original message and only contains the "usefull" information.

#### Send message function:

   Receives a connection and a message as parameters, and procedes to send the message to the specified connection.

#### Receive message function:

   Using the exact_recv function, determines what the original message sent was, and inquires about its type, sending a specific message based on its command parameter.

## Game Structure and Logic

&nbsp;

- ### Playing Area

&nbsp;

- ### Caller

&nbsp;

- ### Player

&nbsp;

## Security implemented in the game

In order to fulfil the security requirements stated in the project description guide we built a module named "security".

The security module is divided into three scripts:

1. security.py
2. vsc_security.py
3. tests.py

In the "security.py" script there are useful functions for generating asymmetric and symmetric keys, signing messages, verifying signatures and encrypt and decrypt messages (numbers).

In the "vsc_security.py" script there are useful functions for signing and validating citizen card (or virtual) signatures, getting certificate data from the card and retrieving the citizen name and number from the certificate.

The "tests.py" script just has some simple tests to check the "security.py" functions. To check the "vsc_security.py" script there's a simple test in its main function.

Going into technical details regarding the module:

- For the assymmetric key generation we used the RSA algorithm with public exponent equal to 65537 (recommended by the **rsa** python module documentation) and key size equal to 2048 (sufficient for the level of security we need to achieve).
- For hash related operations we used SHA256.
- To sign and validate signatures we used the methods **sign** and **verify** of the rsa keys.
- For the symmetric key generation we used the PBKDF2HMAC algorithm with a random generated 32 bit salt, random generated 16 bit password, with length 32, hashing algorithm SHA256 and 100 000 iterations. We didn't store the salt nor the password due to the context of the symmetric key usage (the possibility of the client loosing its symmetric key is 0).
- For the symmetric encryption and decryption we used the AES algorithm with the mode CBC with a random 16 bit IV.
- Regarding the Citizen Card, we used the module PyKCS11 and initialized the session using the first slot of the card and logged in with the pin 1111. Afterwards we used the methods of the session to sign messages and retrive the certificate and its data.

To integrate the security module with the game logic we defined the following rules:

1. Each client (caller or player) must have a **citizen card** in order to sucessfully register into the game. Since we were limited in hardware material, we used the virtual citizen card generator provided by professor João Barraca. In the folder **cards** of the project repository there are folders for each player and caller with their "card" which is a json file.
2. The playing area must have a whitelist of potential callers and only accept a caller which integrates the list.
3. The first message sent to the playing area from any client should be a CertMessage which includes a RegisterMessage, the signature of the RegisterMessage using the private key of the citizen card and the certificate of the citizen card.
4. In every message exchange there should be the following:
   - The person which creates a message should sign it.
   - The person which recieves a message should validate its signature.
   - The person which detects an anomaly should inform the caller which should procede with the disqualification of the person related to the anomaly.
   - If the anomaly comes from the playing area or the caller the game is aborted.

## Conclusion

&nbsp;

## How to Run

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

### Processes
#### Playing Area

The Playing Area (PA) plays a crucial role in the game. It begins by establishing a socket and linking it to a specific address. The PA then listens for incoming connections from other sockets, such as players and the caller. As users connect and register, the PA stores their information, including their public keys and nicknames. The PA also maintains a log of all messages exchanged between users by continuously listening for new connections and messages.
#### Caller

The Caller is a special user who is responsible for managing the players during the game. They are designated as such by the Playing Area (PA), which maintains a list of approved Callers. If a player is accused of cheating, the PA verifies the accusations and may disqualify the player if they are found to have engaged in activities such as using an invalid signature or cheating in the deck shuffling process. The Caller is implemented as a class that is instantiated in run_caller.py, which establishes a socket connection with the PA. The Caller remains in a loop, waiting for messages and triggering certain events, for example, the process for sharing symmetric keys.

#### Player

The player is a user who participates in the game. They have a certain probability of cheating during various stages of the game. Like the Caller, the player is implemented as a class that first connects to the Playing Area (PA) and then waits for messages. When they receive a message, they may act upon it or respond as needed. The player class also has the ability to cheat with a certain probability during different stages of the game.

### Flow of Execution

#### 1. Start of the Game and Authentication

The first script that should be run is Playing Area's script, which starts the registration and authentication processes. Then, the Caller script should be run, since PA is programmed to register the first client socket as Caller (if its REGISTER MESSAGE is followed by a corresponding certificate to validate a Citizen Card as a Caller position). Then, the Player script should be run. When receiving a player's REGISTER MESSAGE, PA will broadcast the message to the Caller, which registers the player if the number of allowed players has not been surpassed. In this whole process, the Caller saves the registered players' data, that is, the PA's attributed ID, its nick, and its public key. 

#### 2. Generation of the Playing Cards and Playing Deck


When all players' slots are full, the Caller sends a command to start the game, using for that effect BEGIN_GAME messages sent to the PA, which contains all ID's of all players registered in the platform, such as public keys (including its own). That message is relayed to each player, in order to allow them to store all participants' public keys.

Then, the Caller starts the deck's creation process, using the function generate_deck(), and sending to the PA the MESSAGE_DECK message with the encrypted deck, which was created by itself. When receiving this message, the PA runs the function deck_generation(), in which it will send the current deck to each player, ordered by ID, so that they proceed to shuffle the deck and encrypt its outcome, number by number, using the shuffle_deck() function. Simultaneously, the players will also generate its Playing Card, through the function generate_playing_card(), sending both the encrypted deck and its Playing Card to the PA, using the COMMIT_CARD message, while both are redirected to the Caller. This process is repeated until all players have had the opportunity to shuffle the deck and generate their Playing Card.
At this point, the PA will send its final deck to the Caller, which in turn in sign it and declare it as the deck to be used in the game.

#### 3. Playing Cards Validation

After signing the Playing Deck to be used in the game, the Caller initiates the process of validating the Playing Cards by sending a message of the type SIGN_FINAL_DECK_ACK, which includes the Playing Cards sent by each player in the previous step. Receiving this message in the Playing Area initiates the execution of the share_sym_keys() function, in which it will request all Players for their symmetric keys to forward to the Caller, who will store them in a data structure. Then it runs the verify_playing_cards() function, in which it sends, one by one, the playing cards to the Players, so that everyone can verify that the cards follow the rules, without anyone cheating. For this, the sending is done using a VERIFY_CARDS message, which triggers the verify_cards() function in the Players, who respond with a VERIFY_CARD_OK message if no one cheated, or a VERIFY_CARD_NOK message with the ID of potential cheaters. After receiving responses from all Players, the Playing Area aggregates the information received in these messages and sends it to the Caller in a CHEAT_VERIFY message, which, based on the conclusions reached by the Players (and itself, since it also ran its verify_cards() function), decides if there are players to be disqualified or not. If there are, it calls the disqualify_player() function, in which a DISQUALIFY message is generated informing the Playing Area and all Players of the disqualification of a player. In response, the Playing Area and Players delete the information related to that player that they have stored in their list of active players, and the disqualified player gracefully ends its process.

#### 4. Playing Deck Validation

At this point, the Caller will begin the next stage of the game, sending the POST_FINAL_DECKS message to the Playing Area, with the symmetric key of each player, as well as the encrypted deck resulting from their shuffle. The Playing Area then executes the verify_playing_deck() function, forwarding this message from the Caller to each Player, one by one, and triggering the decrypt() function in their processes. Therefore, the Players will begin the process of decrypting the deck to verify if any Player cheated while doing the shuffling, with the Caller doing the same thing simultaneously, with the process being very similar to the oen described for the Playing Cards validation. As such, the Playing Area will aggregate the results obtained by the different Players, sending it to the Caller, who will verify if anyone cheated, according to the procedure described before.

In case it's determined that someone cheated in the shuffling, the Caller will consider that the integrity of the game has been compromised, given that the intended original Playing Deck, and therefore the rightful winner, was manipulated. Thus, the Caller will end the game.

#### 5. Finding the Winner

Afterwards, the Caller will send an ASK_FOR_WINNER message to the Playing Area, which will forward it to all the Players in order to determine the winner, by using the find_winner() function. (It's worth pointing out that the Caller had already sent the Playing Cards of all Players to everyone else previously, at the end of stage 2).
The Players will send the ID of the winners they have determined through the WINNER message, that is forwarded to the Caller. When the Caller verifies that all the remaining Players on the game have found a winner, he will check which of the Players have the same winners as he does, disqualifying any Player that reached a different conclusion. In the end, the Caller will inform the Players of the official winner, by sending a WINNER_ACK message. 
It's worth pointing out that the possibility of there being multiple winners is considered, in the case when two players reach Bingo in the same round.

#### 6. End of the Game

After ending the game, the Players and the Caller can request the player list and the action log, or they can end the process, according to the user input.

### Implementation of Cheating
There are 3 main cheating methods implemented in the player code, and each of them send the corresponding cheat message when they, in fact, cheat.

#### 1. Cheating when creating playing card

There is a chance a player will generate a different playing card, one that is not randomly generated and therefore unfair compared to other users. When cheating, the player will create a deck based on the first element of the deck it received, and will have less elements, increasing its chances of winning unfairly.

#### 2. Cheating when shuffling the deck

Since all players need to shuffle the received deck, there is a chance one of those users will shuffle the deck not randomly, but in a way it could be beneficial to them and therefore, be unfair. 

#### 3. Declaring player itself as a winner

There is a chance a player will simply declare itself as the winner of the game, even though we most likely isn't, which is obviously not fair to all the other players who are playing fairly

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
   - The person which receives a message should validate its signature.
   - The person which detects an anomaly should inform the caller which should procede with the disqualification of the person related with the anomaly.
   - If the anomaly comes from the playing area or the caller the game is aborted.

## Conclusion

Through this project we were able to infer about security in authentication, the use of certificates and signatures to increase it using as context the bingo game. Using PTEID we were able to authenticate both players and the caller, and using signed messages we could authenticate the sender of the data that was sent, which holds sensitive information. 
All methods were implemented in case the caller or players cheated, in order to keep the game flowing and disqualify dishonest users.

## How to Run

- ### Requirements

In order to run the game successfully there are some requirements that should be fulfilled.

For linux ubuntu distribution, the instructions are:

```
sudo apt install pcscd
```

```
sudo apt install python3-pip
```

```
sudo apt install swig
```

```
pip3 install --user pykcs11
```

```
sudo apt install opensc-pkcs11
```

```
sudo apt update
sudo apt install autoconf automake build-essential libpcsclite-dev python3-crypto python3-pip libtool help2man
pip3 install argparse cryptography
```

Before doing the following instructions make sure that your distribution default python is pointing to python3.

```
python --version
```

If the output is a version of python2 you must install python3 (if you haven't already installed it):

```
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.8
```

Then, after having python3 in your distribution to set python3 as default python run:

```
sudo apt install python-is-python3
```

The following command should output a python3 version:

```
python --version
```

After making sure your python default is python3 run:

```
git clone https://github.com/jpbarraca/vsmartcard.git
cd vsmartcard
cd virtualsmartcard
autoreconf --verbose --install
./configure --sysconfdir=/etc
make
sudo make install
```

Install the python scripts dependencies:

```
pip3 install -r requirements.txt
```

- ### Running the Code
  Assuming that already all the requirements above were fulfilled we can run the code.

1. On one terminal run the following commands:

   ```
   systemctl stop pcscd
   sudo pcscd -f -d
   ```

   _Note_: this simulates the pluging of the card reader.

&nbsp;

2. On another terminal in the directory **vsmartcard/virtualsmartcard/src/vpicc** run the command:

   ```
   cp path/to/assignment-2---bingo-25/cards/{client}/card.json .
   ./vicc -t PTEID -v
   ```

   _Note_: What this command does is simulate the insertion of an actual citizen card to the card reader. **So to insert a different client card** we must kill the process and change the {client} placeholder in the cp path and run the ./vicc script again.

&nbsp;

3. On another terminal in the directory **assingment-2--bingo-25** run:

   ```
   python3 playing_area/parea.py -p [PLAYING AREA PORT]
   ```

&nbsp;

4. On another terminal in the directory **assingment-2--bingo-25** and **with the caller card inserted** (like in the step 2), run:

   ```
   python3 caller/run_caller.py -p [PLAYING AREA PORT] -n [NICK] -N [Number of cards in Deck] --players [Number of players]
   ```

   _Note_:

   - The caller whitelist can be checked in the README.md of the cards folder.
   - N has default value of 60
   - players has a default value of 4

&nbsp;

5. On another terminal in the directory **assingment-2--bingo-25** and **with the player card inserted** (like in the step 2), run:

   ```
   python3 player/run_player.py -p [PLAYING AREA PORT] -n [NICK]
   ```

_Note_: the game will only being when the number of players defined in step 4 is reached.

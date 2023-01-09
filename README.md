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

&nbsp;

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

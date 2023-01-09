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
   - The person which receives a message should validate its signature.
   - The person which detects an anomaly should inform the caller which should procede with the disqualification of the person related with the anomaly.
   - If the anomaly comes from the playing area or the caller the game is aborted.

## Conclusion

&nbsp;

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

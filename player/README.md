# Player

Contains the player code, including instructions to run it.

## How to run:

1. In one terminal run the following command:

```
sudo pcscd -f -d
```

2. In another terminal run the following commands (already inside the directory vsmartcard/virtualsmartcard/src/vpicc):

```
cp ../../../../assignment-2---bingo-25/cards/calista/card.json .
./vicc -t PTEID -v
```

3. In another terminal run the following commands:

```
    python3 player/run_player.py -p [PLAYING AREA PORT] -n [NICK]
```

## Virtual Card

To insert the Virtual Card the user must copy its json card to the folder local folder:

```
vsmartcard/virtualsmartcard/src/vpicc
```

Afterwards it should run the following command:

```
./vicc -t PTEID -v
```

# Caller

Contains the caller code, including instructions to run it.

## How to run:

1. In one terminal run the following command:

```
sudo pcscd -f -d
```

2. In another terminal run the following commands (already inside the directory vsmartcard/virtualsmartcard/src/vpicc):

```
cp ../../../../assignment-2---bingo-25/cards/aristides/card.json .
./vicc -t PTEID -v
```

3. In another terminal run the following commands:

```
python3 caller/run_caller.py -p [PLAYING AREA PORT] -n [NICK] -N [Number of cards in Deck] --players [Number of players]
```

- N has a default value of 60
- players has a default value of 4

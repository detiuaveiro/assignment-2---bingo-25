from player import Player

if __name__ == "__main__":
    name = input("Enter your name: ")
    p = Player(name, 5011)
    p.connect()
    p.loop()
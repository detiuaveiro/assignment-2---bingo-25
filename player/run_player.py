from player.player import Player

if __name__ == "__main__":
    p = Player("Foo", 8080)
    p.connect()
    p.loop()
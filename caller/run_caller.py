from caller import Caller

if __name__ == "__main__":
    c = Caller("Foo", 5011)
    c.connect()
    c.loop()
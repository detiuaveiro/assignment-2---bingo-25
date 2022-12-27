from caller.caller import Caller

if __name__ == "__main__":
    c = Caller("Foo", 8080)
    c.connect()
    c.loop()
from player import Player
import click

@click.command()
@click.option('--nick', '-n', prompt="Enter your nick, please", help='Port to connect to the Playing Area')
@click.option('--port', '-p', type=int, required=True, help='Port to connect to the Playing Area')
def main(nick, port):
    p = Player(nick, port)
    p.connect()
    p.loop()

if __name__ == "__main__":
    main()
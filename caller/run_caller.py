from caller import Caller
import click

@click.command()
@click.option('--nick', '-n', prompt="Enter your nick, please", help='Port to connect to the Playing Area')
@click.option('--port', '-p', type=int, required=True, help='Port to connect to the Playing Area')
@click.option('--cards', '-N', default=60, type=click.IntRange(0, 100), help='Number of cards (N) to be used')
@click.option('--players', default=4, type=click.IntRange(0, 6), help='Number of players to accept in the game')
def main(nick, port, cards, players):
    c = Caller(nick, port, cards, players)
    c.connect()
    c.loop()

if __name__ == "__main__":
    main()
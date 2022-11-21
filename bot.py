import argparse
import datetime
import sys
import random
import logging
from peewee import SqliteDatabase, Model, CharField, BooleanField, DateTimeField, IntegerField
from mastodon import Mastodon

# ----------------------------- DB Model --------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs.txt"),
        logging.StreamHandler()
    ]
)
db = SqliteDatabase('infos.db')


class Song(Model):
    message = CharField()
    youtube_id = CharField()
    link = CharField(null=True)
    published = BooleanField(default=False)
    creation_date = DateTimeField(default=datetime.datetime.now)
    publication_date = DateTimeField(null=True)

    class Meta:
        database = db


class Suggestion(Model):
    mast_id = IntegerField()
    message = CharField()
    author = CharField()
    treated = BooleanField(default=False)
    creation_date = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db


# ------------------------------- Functions -----------------------------------
def post_mastodon(msg):
    """
    Post a message to Mastodon
    """
    mastodon = Mastodon(
        access_token='token.secret',
        api_base_url='https://botsin.space/'
    )
    mastodon.status_post(msg)


def infos():
    """
    Show info on the db status
    """
    print("Daily music bot:")
    print("{} songs".format(Song.select().count()))
    print("{} songs published".format(Song.select().where(Song.published == True).count()))
    print("Still {} songs to be published".format(Song.select().where(Song.published == False).count()))


def daily():
    """
    Post daily song
    TODO: add check of last publication done in case it was already done today
    """
    songs = list(Song.select().where(Song.published == False))
    if len(songs) == 0:
        logging.info("No more songs to publish, too bad")
        sys.exit(0)
    theone = random.choice(songs)
    if theone.link is None:
        msg = "{} #pouetradio #tootradio \nhttps://youtu.be/{}".format(
            theone.message,
            theone.youtube_id,
        )
    else:
        msg = "{} #pouetradio #tootradio \nhttps://youtu.be/{} \n{}".format(
            theone.message,
            theone.youtube_id,
            theone.link
        )
    logging.info("Message posted : %s", msg)
    theone.published = True
    theone.publication_date = datetime.datetime.now()
    theone.save()


def add(args):
    """
    Adds a new song to the db
    """
    new_song = Song()
    new_song.message = args.MESSAGE
    new_song.youtube_id = args.YOUTUBE_ID
    if args.link:
        new_song.link = args.link
    new_song.save()
    logging.info("Song saved : (%i, %s)", new_song.id, new_song.message)


def check_answer():
    """
    Check messages received and answer + add to suggestions
    """
    mastodon = Mastodon(
        access_token='token.secret',
        api_base_url='https://botsin.space/'
    )

    for notif in mastodon.notifications(exclude_types=["follow", "favourite", "reblog", "poll", "follow_request"]):
        if notif["type"] != "mention":
            continue
        exist = Suggestion.select().where(Suggestion.mast_id == notif["status"]['id'])
        if len(exist) == 0:
            # Never recorded
            sugg = Suggestion()
            sugg.mast_id = notif["status"]['id']
            sugg.message = notif["status"]["content"]
            sugg.author = notif["account"]["acct"]
            sugg.treated = False
            sugg.save()

            mastodon.status_post("Noted, thanks!", in_reply_to_id=notif["status"])
            logging.info("Answered to %s message %i", sugg.author, sugg.mast_id)
    mastodon.notifications_clear()
    logging.debug("Cleared notifications")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Post some daily music sutff')
    subparsers = parser.add_subparsers(dest="command")
    parser_a = subparsers.add_parser('daily', help='Post the daily toot')
    parser_b = subparsers.add_parser('check_answer', help='Check if someone recommended something and add it to suggestions')
    parser_c = subparsers.add_parser('add', help='Add a new song to be published')
    parser_c.add_argument('MESSAGE', help="message")
    parser_c.add_argument('YOUTUBE_ID', help="Youtube id")
    parser_c.add_argument('-l', '--link', help="Additional link to buy / listen")
    parser_d = subparsers.add_parser('info', help='Publish information on activity of this bot')
    args = parser.parse_args()

    db.connect()
    db.create_tables([Song, Suggestion])

    if args.command == "daily":
        daily()
    elif args.command == "check_answer":
        check_answer()
    elif args.command == "add":
        add(args)
    elif args.command == "info":
        infos()
    else:
        parser.print_help()

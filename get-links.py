#!/usr/bin/env python3

# This script will go through one or more channels,
# and get all the image links that have been posted in it
# and put it in a properly labeled file.

from typing import Any, List, Tuple
import argparse
import datetime
import logging
import sqlite3
import json
import glob
import enum
import sys
import io
import os
import re


class LinkType(enum.Enum):
    Imgur = 'imgur.com'
    Gyazo = 'gyazo.com'
    Nuuls = 'nuuls.com'


class LinkData:
    """
    Data about a link.
    """

    def __init__(self,
                 link: str = None,
                 link_type: LinkType = None,
                 specific_id: str = None,
                 user: str = None,
                 channel: str = None,
                 message: str = None,
                 date: datetime.datetime = None,
                 ):
        """All kwargs are required."""
        if link == None or user == None or date == None or channel == None or message == None or specific_id == None or link_type == None:
            raise ValueError(
                "LinkData.__init__() is missing 1 or more kwargs.")
        if not isinstance(link_type, LinkType):
            raise ValueError(
                "kwarg 'link_type' is not part of the LinkType enum.")
        self.link = link
        self.user = user
        self.date = date
        self.channel = channel
        self.specific_id = specific_id
        self.message = message
        self.type = link_type

    def __repr__(self):
        return f"[{self.date}] #{self.channel} {self.user}: {self.raw_link()}"

    def raw_link(self) -> str:
        if self.type == LinkType.Imgur:
            # The '.png' is needed, only tested on imgur.  And if its a gif
            # or something it will still return the proper data (eg. a gif not png)
            return f"https://i.imgur.com/{self.specific_id}.png"
        elif self.type == LinkType.Gyazo:
            return f"https://i.gyazo.com/{self.specific_id}.png"
        elif self.type == LinkType.Nuuls:
            return f"https://i.nuuls.com/{self.specific_id}.png"
        raise ValueError("Invalid link type.")

    def to_json_serializable(self) -> dict:
        """
        Returns the link data as something that can be JSON serialized.
        """
        out = self.__dict__
        out['raw_link'] = self.raw_link()
        out["type"] = self.type.value
        out["date"] = self.date.isoformat()
        return out


def get_logfile_info(path: str) -> Tuple[str, datetime.date]:
    """
    Gets the channel, and date a log file is of.
    """

    findDateRegex: re.Pattern = re.compile(
        r"^([^-]*)-((\d{4})-(\d{2})-(\d{2}))\.log$")
    # example basename 'quinndt-2021-05-26.log'
    basename = os.path.basename(path)
    DateMatch = findDateRegex.match(basename)

    if not DateMatch:
        raise ValueError(
            "Logfile filename does not match patern, cannot extract date.")

    FileDate = datetime.date(
        *[int(n) for n in [DateMatch.group(3), DateMatch.group(4), DateMatch.group(5)]])
    return DateMatch.group(1), FileDate


def parse_line(line: str, asumeDate: datetime.date) -> Tuple[str, str, datetime.datetime]:
    """
    Parses the line, getting some metadata.
    Only works on messages, however the date will always be correct.

    Returns the user, message, and date.
    """
    user, _, message = line[12:].partition(": ")
    if not user.isascii():
        # People who have Japanese/Korean/Chinese names
        # The names are in the format "<Special Character Name> <Real Username>"
        # And for some reason (!!!) these names only have one space before them, not 2.
        user = user.split(" ")[1]

    hour, _, rest = line[1:9].partition(":")
    mins, _, second = rest.partition(":")

    messageDate = datetime.datetime(
        asumeDate.year, asumeDate.month, asumeDate.day, int(hour), int(mins), int(second))
    return user, message, messageDate


def get_links(logfile: str) -> List[LinkData]:
    """
    Get all image links present from log file.
    """
    links: List[LinkData] = []
    channel, fileDate = get_logfile_info(logfile)

    linkRegex = re.compile(
        # When updating: Group 3 must be the host name, and group 4 be the specific ID.
        # If possible move to named capture groups but I couldnt get those to work.
        r"(https?://)?(i\.)?(imgur\.com|gyazo\.com|(?<=i\.)nuuls\.com)/([\w\-]*)(\.\w*)?"
    )
    lines = []
    with io.open(logfile, "r", encoding='utf-8') as f:
        try:
            lines = f.readlines()
        except UnicodeDecodeError:
            logging.info(
                f"Unable to decode file '{os.path.basename(logfile)}'. - Skipping")
    for line in lines:
        # Comments, things like noting logging start time and timezone.
        if line.startswith('#'):
            continue

        match = linkRegex.finditer(line)
        for _, match in enumerate(match):
            fullLink = match.group(0)
            # Group 3 will be the hostname, and 4 the specific id.
            linkType = LinkType(match.group(3))
            imageID = match.group(4)
            try:
                user, message, messageDate = parse_line(line, fileDate)
            except ValueError:
                # This can happen when the line isnt properly formatted
                # As chatterino seems to sometimes absolutely FUCK the output lol
                logging.debug("Unable to parse line: " +
                              line.replace('\n', ''))
                continue

            if user.count(" ") != 0:
                # Very spammy

                # logging.debug(
                #     "Skipping line because username contains space: " + line.replace('\n', ''))
                continue

            links.append(LinkData(
                channel=channel,
                message=message,
                specific_id=imageID,
                user=user,
                link=fullLink,
                link_type=linkType,
                date=messageDate
            ))
    return links


def get_all_files(channels: List[str], logs_dir: str) -> List[List[str]]:
    """
    Returns a list of lists of files in each channel
    """
    logs_dir = os.path.abspath(logs_dir)
    if not os.path.exists(logs_dir):
        raise FileNotFoundError(f"Logs directory '{logs_dir}' does not exist.")
    all_files: List[List[str]] = []

    for channel in channels:
        files: List[str] = []
        files_dir = os.path.join(logs_dir, "Twitch", "Channels", channel)

        if not os.path.exists(files_dir):
            logging.warning(f"Channel '{channel}' does not have logs.")

        files = glob.glob(os.path.join(files_dir, "*"))
        all_files.append(files)
    return all_files


def filter_and_format_links(links: List[LinkData]) -> List[LinkData]:
    """Filters & formats links.
    """
    newLinks: List[LinkData] = []

    for link in links:
        # Filtering:
        if link.specific_id == "a" and link.type == LinkType.Imgur:
            # List of images "https://imgur.com/a/Some_ID"
            continue

        if link.specific_id == "gallery" and link.type == LinkType.Imgur:
            # List of images "https://imgur.com/gallery/Gallery_ID"
            continue

        if link.specific_id == "upload" and link.type == LinkType.Imgur:
            continue

        if link.specific_id == "thumb" and link.type == LinkType.Gyazo:
            # Different sizes "https://i.gyazo.com/thumb/1200/IMAGE_ID-png.jpg"
            continue

        # Formatting:
        link.message = link.message.replace('\n', '')

        newLinks.append(link)

    return newLinks


def get_all_links(channels: List[LinkData], logs_dir: str) -> List[LinkData]:
    links: List[LinkData] = []

    all_files = get_all_files(channels, logs_dir)
    for i in range(len(all_files)):
        for file in all_files[i]:
            links.extend(get_links(file))

    return filter_and_format_links(links)


def save_links_db(links: List[LinkData], args: dict) -> int:
    conn = sqlite3.connect(args['out_file'])
    cur = conn.cursor()
    # Create table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS `images` (
            `ID` INTEGER PRIMARY KEY AUTOINCREMENT,
            `Specific_ID` VARCHAR(50) NOT NULL,
            `Link` VARCHAR(150) NOT NULL,
            `Link_Type` VARCHAR(50) NOT NULL,
            `Raw_Link` VARCHAR(150) NOT NULL,
            `Date_Posted` DATETIME NOT NULL,
            `User_Posted` VARCHAR(50) NOT NULL,
            `Channel_Posted` VARCHAR(50) NOT NULL,
            `Message_Text` TEXT NOT NULL
        )
        ;
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS `UNIQUE_ENTRIES_IN_IMAGES` ON `images` (
            `Specific_ID`, `Link_Type`,
            `Date_Posted`, `User_Posted`, `Channel_Posted`, `Message_Text`
            )
        """
    )
    # And now insert.
    cursor = cur.executemany(
        """
        INSERT OR REPLACE INTO `images` (
            Specific_ID, Link, Link_Type, Raw_Link, Date_Posted, User_Posted, Channel_Posted, Message_Text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [(link.specific_id, link.link, link.type.value, link.raw_link(), link.date.isoformat(), link.user, link.channel, link.message.replace('\n', '').replace('\r', '')) for link in links]
    )

    # Bruh I forgot to do this and I was debugging for like 20 mins
    cursor.fetchall()
    conn.commit()
    return cursor.rowcount


def save_links_json(links: List[LinkData], args: dict) -> int:
    kwargs = {}
    if args['file_format'] == "pretty-json":
        kwargs['indent'] = 2

    output_obj = {
        'total': len(links),
        'created': datetime.datetime.now().isoformat(),
        'channels': args['channels'],
        'links': [link.to_json_serializable() for link in links]
    }

    json.dump(output_obj,
              fp=open(args['out_file'], "w"), **kwargs)

    return len(links)


def save_links(links: List[LinkData], args: dict):
    if args['file_format'] == "sql":
        return save_links_db(links, args)
    elif args['file_format'].count("json") > 0:
        return save_links_json(links, args)


def verify_args(args: Any) -> dict:
    logs_dir: str = os.path.abspath(args.logs_dir)
    if not os.path.exists(logs_dir):
        raise FileNotFoundError(f"Logs directory '{logs_dir}' does not exist.")

    channels = [i.lower() for i in args.channels]
    for channel in channels:
        if channel.count("*") != 0:
            channelsGlob = os.path.join(
                logs_dir, "Twitch", "Channels", channel)
            logging.info(f"Channels captured from '{channel}':   " +
                         ",  ".join([os.path.basename(i) for i in glob.glob(channelsGlob)]))

    return {
        'channels': channels,
        'skip_prompt': args.skip_prompt,
        'file_format': args.file_format.lower(),
        'out_file': os.path.abspath(
            args.out_file if args.out_file is not None else './images.db' if args.file_format.lower() == "sql" else "./images.json"),
        'logs_dir': logs_dir
    }


def main(args):
    """
    Get image links from twitch chat logs created from chatterino.
    """
    args = verify_args(args)

    links = get_all_links(args['channels'], args['logs_dir'])
    logging.info(f"Total number of links: {len(links)}")

    if len(links) >= 1000:
        answer = "some random dummy data"
        while not args['skip_prompt'] and answer.lower() not in ["yes", "y", ""]:
            filetype = "an SQLite3 database"
            if args["file_format"].count("json") > 0:
                filetype = args["file_format"]
            answer = input(
                f"Write all {len(links)} links as {filetype} to '{args['out_file']}' (Y/n): ")
            if answer.lower() in ["n", "no"]:
                logging.critical("Aborting.")
                sys.exit(0)

    number_saved = save_links(links, args)
    logging.info(
        f"Saved {number_saved if type(number_saved) == int else 0} as {args['file_format']} to {os.path.basename(args['out_file'])}.")


def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Get image links from twitch chat logs created from chatterino.',
        epilog='When saving 1000 or more image links there is a confirmation prompt.'
    )
    parser.add_argument("-l", "--logs-dir",
                        help="The directory of chatterino logs. Should contain folder 'Twitch'.  Default is '.'.",
                        default=".",
                        required=False,
                        dest='logs_dir'
                        )
    parser.add_argument("-y", "--yes",
                        help="When prompted for anything, assume yes.",
                        action='store_true',
                        default=False,
                        required=False,
                        dest='skip_prompt'
                        )
    parser.add_argument("-f", "--format",
                        help="Output file format. Default 'sql' (sqlite3).",
                        default='sql',
                        choices=['pretty-json', 'json', 'sql'],
                        required=False,
                        dest='file_format'
                        )
    parser.add_argument("-o", "--output",
                        help="The file to store the output in. Default './images.db' or './images.json'.",
                        required=False,
                        dest='out_file'
                        )
    parser.add_argument("-c", "--channels",
                        help="One or more channels to get links from.",
                        required=True,
                        nargs='+',
                        metavar="CHANNEL"
                        )
    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(name)s] %(levelname)8s: %(msg)s")

    parser = get_arg_parser()
    args = parser.parse_args()
    main(args)

# image-finder

Finds image links in chatterino logs.

This script will find image links and related data about them, and put them into either a JSON file, or a SQLite3 database (default).

## Usage

To get images from channel `foo` and all channels that start with `bar`. In a pretty JSON format.
Replace `pretty-json` with `json` to save drive space. (~70 bytes per link)

```txt
./get-links.py -l /path/to/logs -f pretty-json -c foo bar*
```

Example output in `./images.json`

```json
{
  "total": 2,
  "created": "2021-07-22T01:20:00.846648",
  "channels": ["foo", "bar*"],
  "links": [
    {
      "link": "https://i.imgur.com/IMGUR_ID.png",
      "user": "pogchamp_guy",
      "date": "2020-07-20T11:34:40",
      "channel": "foo",
      "specific_id": "IMGUR_ID",
      "message": "PogChamp https://i.imgur.com/IMGUR_ID.png",
      "type": "imgur.com",
      "raw_link": "https://i.imgur.com/IMGUR_ID.png"
    },
    {
      "link": "https://imgur.com/IMGUR_ID",
      "user": "barry",
      "date": "2020-07-20T11:39:48",
      "channel": "barry",
      "specific_id": "IMGUR_ID",
      "message": "https://imgur.com/IMGUR_ID oh nice its wokring",
      "type": "imgur.com",
      "raw_link": "https://i.imgur.com/IMGUR_ID.png"
    }
  ]
}
```

Command line help:

```txt
usage: get-links.py [-h] [-l LOGS_DIR] [-y] [-f {pretty-json,json,sql}] [-o OUT_FILE] -c CHANNEL [CHANNEL ...]

Get image links from twitch chat logs created from chatterino.

optional arguments:
  -h, --help            show this help message and exit
  -l LOGS_DIR, --logs-dir LOGS_DIR
                        The directory of chatterino logs. Should contain folder 'Twitch'. Default is '.'.
  -y, --yes             When prompted for anything, assume yes.
  -f {pretty-json,json,sql}, --format {pretty-json,json,sql}
                        Output file format. Default 'sql' (sqlite3).
  -o OUT_FILE, --output OUT_FILE
                        The file to store the output in. Default './images.db' or './images.json'.
  -c CHANNEL [CHANNEL ...], --channels CHANNEL [CHANNEL ...]
                        One or more channels to get links from.

When saving 1000 or more image links there is a confirmation prompt.
```

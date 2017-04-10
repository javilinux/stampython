#!/usr/bin/env python
# encoding: utf-8
#
# Description: Plugin for processing XKCD's strip requests
# Author: Pablo Iranzo Gomez (Pablo.Iranzo@gmail.com)

import datetime
import logging
import dateutil.parser
import feedparser
from lxml import html
from apscheduler.schedulers.background import BackgroundScheduler

import stampy.stampy
import stampy.plugin.stats
import stampy.plugin.config
from stampy.i18n import translate
_ = translate.ugettext

sched = BackgroundScheduler()
sched.start()


def init():
    """
    Initializes module
    :return: List of triggers for plugin
    """

    sched.add_job(xkcd, 'cron', id='xkcd', hour='17', replace_existing=True,
                  misfire_grace_time=120)

    return "/xkcd"


def run(message):  # do not edit this line
    """
    Executes plugin
    :param message: message to run against
    :return:
    """
    text = stampy.stampy.getmsgdetail(message)["text"]
    if text:
        if text.split()[0].lower() == "/xkcd":
            xkcdcommands(message=message)
    return


def help(message):  # do not edit this line
    """
    Returns help for plugin
    :param message: message to process
    :return: help text
    """
    commandtext = _("Use `/xkcd <date>` to get xkcd's comic strip for date or today (must be on RSS feed)\n\n")
    if stampy.plugin.config.config(key='owner') == stampy.stampy.getmsgdetail(message)["who_un"]:
        commandtext = _("Use `/xkcd trigger` to force sending actual strip to channel\n\n")
    return commandtext


def xkcdcommands(message):
    """
    Searches for commands related to dilbert
    :param message: message to process
    :return:
    """

    logger = logging.getLogger(__name__)
    msgdetail = stampy.stampy.getmsgdetail(message)

    texto = msgdetail["text"]
    chat_id = msgdetail["chat_id"]
    message_id = msgdetail["message_id"]
    who_un = msgdetail["who_un"]

    logger.debug(msg=_("Command: %s by %s") % (texto, who_un))

    # We might be have been given no command, just /dilbert
    try:
        date = texto.split(' ')[1]
    except:
        date = ""

    if stampy.plugin.config.config(key='owner') == stampy.stampy.getmsgdetail(message)["who_un"] and date == "trigger":
        # We've been called to update the strip channel
        return xkcd()

    try:
        # Parse date or if in error, use today
        date = dateutil.parser.parse(date)

        # Force checking if valid date
        day = date.day
        month = date.month
        year = date.year
        date = datetime.datetime(year=year, month=month, day=day)
    except:
        date = datetime.datetime.now()

    return xkcd(chat_id=chat_id, date=date, reply_to_message_id=message_id)


def xkcd(chat_id=-1001105187138, date=None, reply_to_message_id=""):
    """
    Sends XKCD's strip for the date provided
    :param chat_id: chat to send image to
    :param date: date to get the strip from that day
    :param reply_to_message_id: Id of the message to send reply to
    :return:
    """

    logger = logging.getLogger(__name__)

    url = "https://xkcd.com/atom.xml"

    # Ping chat ID to not have chat removed
    stampy.plugin.stats.pingchat(chat_id)

    if not date:
        date = datetime.datetime.now()

    feed = feedparser.parse(url)
    tira = []
    for item in reversed(feed["entries"]):
        dateitem = dateutil.parser.parse(item["updated"][:16])
        if date.year == dateitem.year and date.month == dateitem.month and \
           date.day == dateitem.day:
            tira.append(item)

    logger.debug(msg=_("# of Comics for today: %s") % len(tira))

    for item in tira:
        url = item['link']
        tree = html.fromstring(item['summary'])
        imgsrc = tree.xpath('//img/@src')[0]
        imgtxt = item['title_detail']['value'] + "\n" + url + " - @redken_strips"
        stampy.stampy.sendimage(chat_id=chat_id, image=imgsrc, text=imgtxt, reply_to_message_id=reply_to_message_id)
    return
"""Code that sends data to user after operating...
Right now uses telegram via telegram - send, a python package """

# Currently assumes telegram-send has been setup; which can be done
# on a command line from the virtualenv: telegram-send --config
#
# This puts droppings into XDG stuff or ~/Library/Application Support/ on Mac

# this is a ridiculously thin wrapper, doesn't now need its' own module, but
# there could be some formatting and other sort of code, or other ways to send... tbd


import telegram_send


def send(message):
    """Send 'message' using telegram_send"""
    telegram_send.send(messages=[message])

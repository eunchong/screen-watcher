import os
from slacker import Slacker


def send_slack_msg(slack_channel: str, message: str = "") -> None:
    """
    General purpose function to send one-off Slack messages.
    :param slack_channel: Slack channel for message
    :param message: Message to send to Slack
    :return:
    """

    token = os.getenv("SLACK_BOT_TOKEN")
    slack = Slacker(token)
    slack.chat.post_message(slack_channel, message)

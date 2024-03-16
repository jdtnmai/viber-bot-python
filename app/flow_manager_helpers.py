import json
from logger import logger


def parse_json(json_string):
    try:
        parsed_string = json.loads(json_string)
    except json.JSONDecodeError as e:
        parsed_string = {}
    return parsed_string


def get_message_media(message_dict):
    if "media" in message_dict.keys():
        media_link = message_dict["media"]
        return media_link
    return ""


def parse_tracking_data(message_dict):
    if "tracking_data" in message_dict.keys():
        tracking_data_json = message_dict["tracking_data"]
        tracking_data = parse_json(tracking_data_json)
        return tracking_data

    return {}

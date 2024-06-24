import json
from app.data_classes import Intention, IntentionName, ViberMessage
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


def get_message_media(message_dict):
    media_link = message_dict.get("media", "")
    return media_link


def parse_viber_request(viber_request) -> ViberMessage:
    if isinstance(viber_request, ViberMessage):
        return viber_request
    else:
        message_dict = viber_request.message.to_dict()
        return ViberMessage(
            sender_viber_id=viber_request.sender.id,
            message_text=message_dict["text"],
            media_link=get_message_media(message_dict),
            tracking_data=parse_tracking_data(message_dict),
        )


def get_message_intention(message_text):
    text = message_text.lower()
    intentions = Intention()
    intentions.ask_question = (
        text.lower().strip().startswith(IntentionName.ask_question)
    )
    intentions.list_unanswered_question = (
        text.lower().strip().startswith(IntentionName.list_unanswered_question)
    )
    intentions.welcome_help = (
        text.lower().strip().startswith(IntentionName.welcome_help)
    )

    return intentions


def extract_number_from_string(s):
    number = ""
    for char in s:
        if char.isdigit():
            number += char
        else:
            break  # Stop iterating when a non-digit character is encountered
    if number:
        return str(int(number))

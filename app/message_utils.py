import json
from typing import Dict
from logger import logger

from viberbot import Api
from viberbot.api.messages.text_message import TextMessage


class MessageBuilder:
    @staticmethod
    def build_viber_message(message_text: str, tracking_data: Dict) -> TextMessage:
        viber_message = TextMessage(
            tracking_data=json.dumps(tracking_data), text=message_text
        )
        return viber_message


class MessageSenger:
    @staticmethod
    def send_viber_messagess(
        viber: Api, recipient_viber_id: str, viber_message: TextMessage
    ):
        response = viber.send_messages(recipient_viber_id, [viber_message])
        return response

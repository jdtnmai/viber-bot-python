from app.constants import WELCOME_HELP_MESSAGE
from app.message_utils import MessageBuilder, MessageSenger
from app.viber_chat_bot_logic import get_message_media
from app.flow_manager_helpers import parse_tracking_data

from dataclasses import dataclass, asdict


@dataclass
class ViberMessage:
    sender_viber_id: str
    message_text: str
    media_link: str
    tracking_data: dict


class Intention:
    ask_question: bool = False
    list_unanswered_question: bool = False
    answer_question: bool = False
    welcome_help: bool = False


class TrackingData:
    conversation_id: int = None
    system_message: bool = False


class FlowManager:

    def __init__(self, session, viber, viber_request):
        self.session = session
        self.viber = viber
        self.viber_message = self.parse_viber_request(viber_request=viber_request)

    @staticmethod
    def parse_viber_request(viber_request):
        message_dict = viber_request.message.to_dict()
        return ViberMessage(
            sender_viber_id=viber_request.sender.id,
            message_text=message_dict["text"],
            media_link=get_message_media(message_dict),
            tracking_data=parse_tracking_data(message_dict),
        )

    @staticmethod
    def get_message_intention(message_text):
        text = message_text.lower()
        intentions = Intention()
        intentions.ask_question = text.startswith("klausimas")
        intentions.list_unanswered_question = text.startswith("neatsakyti klausimai")
        intentions.welcome_help = text.startswith("labas")

        return intentions

    def welcome_help_flow(self):
        welcome_help_message_text = WELCOME_HELP_MESSAGE
        tracking_data = TrackingData()
        tracking_data.system_message = True

        viber_message = MessageBuilder.build_viber_message(
            message_text=welcome_help_message_text,
            tracking_data=asdict(tracking_data),
        )
        MessageSenger.send_viber_messagess(
            viber=self.viber,
            recipient_viber_id=self.viber_message.sender_viber_id,
            viber_message=viber_message,
        )

    def ask_question_flow(self):
        """
        create conversation
        create question
        select rensponder
        send message to responder
        """
        ...

    def list_unanswered_question_flow(self): ...

    def review_flow(self): ...

    def execute_flow(self):
        """
        figure out message type
        1. initiation_message
        2. isit an ongoing conversation
        """
        self.intetions = self.get_message_intention(self.message_text)

        if self.intentions.welcome_help:
            self.welcome_help_flow()
        elif self.intentions.ask_question:
            self.ask_question_flow()
        elif self.intentions.list_unanswered_question:
            self.list_unanswered_question_flow()
        elif self.viber_message.tracking_data:
            ...

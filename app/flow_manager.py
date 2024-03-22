from app.constants import (
    QUESTION_PREFIX,
    UNANSWERED_QUESTIONS_PREFIX,
    WELCOME_HELP_MESSAGE,
)
from app.message_utils import MessageBuilder, MessageSenger
from app.postgre_entities import (
    create_new_conversation,
    create_question,
    get_questions_without_approved_answers,
    get_users_not_in_active_pending_conversations,
)
from app.viber_chat_bot_logic import get_message_media
from app.flow_manager_helpers import parse_tracking_data

from dataclasses import dataclass, asdict


@dataclass
class ViberMessage:
    sender_viber_id: str
    message_text: str
    media_link: str
    tracking_data: dict


@dataclass
class Intention:
    ask_question: bool = False
    list_unanswered_question: bool = False
    answer_question: bool = False
    welcome_help: bool = False


@dataclass
class IntentionName:
    ask_question: str = "klausimas"
    list_unanswered_question: str = "neatsakyti klausimai"
    answer_question: str = "atsakymas"  # don't remember the meaning
    welcome_help: str = "labas"


@dataclass
class TrackingData:
    conversation_id: int = None
    system_message: bool = False
    flow: str = None
    unanswered_question_ids: dict = None


@dataclass
class ConversationStatus:
    active: str = "active"
    pending: str = "pending"
    closed: str = "closed"


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
        tracking_data = TrackingData(system_message=True)

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
        select rensponder. Respondes is not involved in an active conversation.
        send message to responder
        """
        question = create_question(
            session=self.session,
            question_text=self.viber_message.message_text,
            user_id=self.viber_message.sender_viber_id,
        )
        responders = get_users_not_in_active_pending_conversations(self.session)
        if responders:
            responder = responders.pop()
            conversation = create_new_conversation(
                session=self.session,
                question_id=question.question_id,
                asker_user_id=self.viber_message.sender_viber_id,
                responder_user_id=responder.user_id,
                status=ConversationStatus.active,
            )
            tracking_data = TrackingData(conversation_id=conversation.conversation_id)

            viber_message = MessageBuilder.build_viber_message(
                message_text=QUESTION_PREFIX + question.question_text,
                tracking_data=asdict(tracking_data),
            )

            MessageSenger.send_viber_messagess(
                viber=self.viber,
                recipient_viber_id=responder.sender_viber_id,
                viber_message=viber_message,
            )

        else:
            # there are no active responders, what do we do? should we freeze the status and wait for an active responder?
            #
            conversation = create_new_conversation(
                session=self.session,
                question_id=question.question_id,
                asker_user_id=self.viber_message.sender_viber_id,
                status=ConversationStatus.pending,
            )

    def list_unanswered_question_flow(self):
        unanswered_questions = get_questions_without_approved_answers(self.session)
        message_text = UNANSWERED_QUESTIONS_PREFIX + "\n".join(
            [f"{idx}. {q.question_text}" for idx, q in enumerate(unanswered_questions)]
        )
        unanswered_question_ids = {
            idx: q.question_text for idx, q in enumerate(unanswered_questions)
        }
        tracking_data = TrackingData(
            system_message=True,
            flow=IntentionName.list_unanswered_question,
            unanswered_question_ids=unanswered_question_ids,
        )
        viber_message = MessageBuilder.build_viber_message(
            message_text=message_text,
            tracking_data=asdict(tracking_data),
        )
        MessageSenger.send_viber_messagess(
            viber=self.viber,
            recipient_viber_id=self.viber_message.sender_viber_id,
            viber_message=viber_message,
        )

    def review_flow(self): ...

    def execute_flow(self):
        """
        figure out message type
        1. initiation_message
        2. isit an ongoing conversation
        """
        self.intetions = self.get_message_intention(self.message_text)

        if self.intentions.welcome_help:  # DONE
            self.welcome_help_flow()
        elif self.intentions.ask_question:  # DONE
            self.ask_question_flow()
        elif self.intentions.list_unanswered_question:  # DONE
            self.list_unanswered_question_flow()
        elif (
            self.viber_message.tracking_data
        ):  # we accept answer, or reply to the unanswered question list
            ...
        else:
            self.welcome_help_flow()

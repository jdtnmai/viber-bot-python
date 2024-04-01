from app.flows.constants import (
    UNANSWERED_QUESTIONS_PREFIX,
)
from app.data_classes import (
    ConversationStatus,
    IntentionName,
    TrackingData,
)
from app.flows.flow_accept_or_reject_answer import (
    approve_answer_and_close_conversation,
    handle_reject_response,
)
from app.flows.flow_answer_question import handle_responder_answer
from app.flows.flow_ask_question import (
    get_asker,
    initiate_conversation,
    select_responder,
    send_question_to_responder,
)
from app.flows.flow_list_unanswered_questions import get_and_send_unanswered_questions
from app.flows.flow_welcome_help import send_welcome_help_message
from app.message_utils import MessageBuilder, MessageSenger
from app.data_models import (
    create_question,
    get_conversation_by_id,
    get_questions_without_approved_answers,
    get_user_by_viber_id,
    update_conversation,
)
from app.flows.flow_manager_helpers import (
    get_message_intention,
    parse_viber_request,
)

from dataclasses import asdict

from logger import logger


class FlowManager:

    def __init__(self, session, viber, viber_request):
        self.session = session
        self.viber = viber
        self.viber_message = parse_viber_request(viber_request=viber_request)
        self.intentions = get_message_intention(self.viber_message.message_text)

    def welcome_help_flow(self):
        send_welcome_help_message(self.viber, self.viber_message)

    def ask_question_flow(self):

        asker = get_asker(self.session, self.viber_message.sender_viber_id)
        if not asker:
            logger.debug(
                f"Asker not found for viber_id {self.viber_message.sender_viber_id}. Message {asdict(self.viber_message)}"
            )

        question = create_question(
            self.session, self.viber_message.message_text, asker.user_id
        )

        responder = select_responder(self.session, asker)

        conversation, send_question = initiate_conversation(
            self.session, asker, responder, question
        )
        logger.debug(f"send_question {send_question}")
        if send_question:
            send_question_to_responder(self.viber, responder, conversation, question)

    def answer_question_flow(self):
        conversation = get_conversation_by_id(
            self.session, self.viber_message.tracking_data["conversation_id"]
        )
        message_sender = get_user_by_viber_id(
            self.session, self.viber_message.sender_viber_id
        )
        if conversation.asker_user_id == message_sender.user_id:
            self.accept_answer_flow()

        if conversation.responder_user_id == message_sender.user_id:
            handle_responder_answer(
                session=self.session,
                viber=self.viber,
                conversation=conversation,
                viber_message=self.viber_message,
            )

    def accept_answer_flow(self):

        conversation = get_conversation_by_id(
            self.session, self.viber_message.tracking_data["conversation_id"]
        )
        message_sender = get_user_by_viber_id(
            self.session, self.viber_message.sender_viber_id
        )
        if self.viber_message.message_text.lower().strip().startswith("taip"):
            """
            answer approved
            conversation status close
            """
            approve_answer_and_close_conversation(self.session, conversation)

        elif self.viber_message.message_text.lower().strip().startswith("ne"):
            """
            reject answer
            """

            conversation = update_conversation(
                self.session,
                conversation_id=conversation.conversation_id,
                responder_user_id=None,
                answer_id=None,
                status=ConversationStatus.active,
            )

            handle_reject_response(
                self.session, self.viber, conversation, message_sender
            )

    def list_unanswered_question_flow(self):
        get_and_send_unanswered_questions(self.session, self.viber, self.viber_message)

    def review_flow(self):
        """
        review every message and send system message to nudge users to reply to a message
        """
        ...

    def handle_tracking_data_flow(self):
        tracking_flow = self.viber_message.tracking_data.get("flow")
        if tracking_flow == IntentionName.ask_question:
            if self.viber_message.tracking_data["system_message"] == False:
                self.answer_question_flow()
            elif self.viber_message.tracking_data["system_message"] == True:
                self.accept_answer_flow()
            else:
                self.welcome_help_flow()
        elif tracking_flow == IntentionName.list_unanswered_question:
            self.list_unanswered_question_flow()
        else:
            self.welcome_help_flow()

    def execute_flow(self):
        if self.intentions.welcome_help:
            self.welcome_help_flow()
        elif self.intentions.ask_question:
            self.ask_question_flow()
        elif self.intentions.list_unanswered_question:
            self.list_unanswered_question_flow()
        elif self.viber_message.tracking_data:
            self.handle_tracking_data_flow()
        else:
            self.welcome_help_flow()

from typing import Tuple
from app.flows.constants import (
    ANSWER_PREFIX,
    QUESTION_PREFIX,
    UNANSWERED_QUESTIONS_PREFIX,
    WELCOME_HELP_MESSAGE,
)
from app.data_classes import (
    ConversationStatus,
    Intention,
    IntentionName,
    TrackingData,
    ViberMessage,
)
from app.flows.flow_ask_question import (
    get_asker,
    initiate_conversation,
    select_responder,
    send_question_to_responder,
)
from app.message_utils import MessageBuilder, MessageSenger
from app.data_models import (
    ChatBotUser,
    Conversation,
    Question,
    create_answer,
    create_new_conversation,
    create_question,
    get_answer,
    get_conversation_by_id,
    get_question,
    get_questions_without_approved_answers,
    get_user_by_user_id,
    get_user_by_viber_id,
    get_users_not_in_active_pending_conversations,
    update_answer,
    update_conversation,
)
from app.flows.flow_manager_helpers import get_message_media
from app.flows.flow_manager_helpers import parse_tracking_data

from dataclasses import asdict

from logger import logger


class FlowManager:

    def __init__(self, session, viber, viber_request):
        self.session = session
        self.viber = viber
        self.viber_message = self.parse_viber_request(viber_request=viber_request)
        self.intentions = self.get_message_intention(self.viber_message.message_text)

    @staticmethod
    def parse_viber_request(viber_request):
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

    @staticmethod
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
        """
        1. Must be a conversation. take the conversation
        check who send the message, if the responder, follow answer update flow
        if the sender can be a confirmation message, check does it confirm or rejects
        2. check if question in the conversation has answer.
        3. if message is xxx finalize the answer and share the answer with the asker. Ask does he accepts the answer. send
        4. if the message is text. and the answer exists, append answer text. dont send
        5. if answer does not exist, create answer. dont send
        """
        conversation = get_conversation_by_id(
            self.session, self.viber_message.tracking_data["conversation_id"]
        )
        message_sender = get_user_by_viber_id(
            self.session, self.viber_message.sender_viber_id
        )
        if conversation.responder_user_id == message_sender.user_id:
            if conversation.answer_id is None:
                answer = create_answer(
                    self.session,
                    self.viber_message.message_text,
                    conversation.question_id,
                    conversation.responder_user_id,
                )
                conversation = update_conversation(
                    session=self.session,
                    conversation_id=conversation.conversation_id,
                    answer_id=answer.answer_id,
                    status=ConversationStatus.active,
                )
            elif (conversation.answer_id is not None) and (
                self.viber_message.message_text.lower().strip() == "xxx"
            ):
                answer = get_answer(self.session, conversation.answer_id)
                message_text = ANSWER_PREFIX + answer.answer_text
                tracking_data = TrackingData(
                    conversation_id=conversation.conversation_id,
                    system_message=False,
                    flow=IntentionName.answer_question,
                )
                answer_message = MessageBuilder.build_viber_message(
                    message_text=message_text, tracking_data=asdict(tracking_data)
                )
                asker = get_user_by_user_id(
                    session=self.session, user_id=conversation.asker_user_id
                )
                MessageSenger.send_viber_messagess(
                    self.viber,
                    recipient_viber_id=asker.viber_id,
                    viber_message=answer_message,
                )

                tracking_data = TrackingData(
                    conversation_id=conversation.conversation_id,
                    system_message=True,
                    flow=IntentionName.answer_question,
                )
                answer_acceptance_message = MessageBuilder.build_viber_message(
                    message_text="Ar priimate atsakymą?\nAtsakykite taip arba ne.",
                    tracking_data=asdict(tracking_data),
                )

                MessageSenger.send_viber_messagess(
                    self.viber,
                    recipient_viber_id=asker.viber_id,
                    viber_message=answer_acceptance_message,
                )

                conversation = update_conversation(
                    session=self.session,
                    conversation_id=conversation.conversation_id,
                    status=ConversationStatus.waiting_for_approval,
                )

            elif conversation.answer_id is not None:
                answer = get_answer(self.session, conversation.answer_id)
                updated_answer_text = (
                    answer.answer_text + "\n " + self.viber_message.message_text
                )
                answer = update_answer(
                    self.session, answer.answer_id, answer_text=updated_answer_text
                )

        if conversation.asker_user_id == message_sender.user_id:
            self.accept_answer_flow()

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

    def accept_answer_flow(self):
        conversation = get_conversation_by_id(
            self.session, self.viber_message.tracking_data["conversation_id"]
        )
        message_sender = get_user_by_viber_id(
            self.session, self.viber_message.sender_viber_id
        )
        if self.viber_message.message_text.lower().strip().startswith("taip"):
            """
            conversation status close
            answer approved
            """
            update_answer(self.session, conversation.answer_id, approved=True)
            conversation = update_conversation(
                self.session,
                conversation_id=conversation.conversation_id,
                status=ConversationStatus.closed,
            )
        elif self.viber_message.message_text.lower().strip().startswith("ne"):
            """
            conversation status close
            answer approved
            """
            conversation = update_conversation(
                self.session,
                conversation_id=conversation.conversation_id,
                responder_user_id=None,
                answer_id=None,
                status=ConversationStatus.active,
            )
            responders = get_users_not_in_active_pending_conversations(self.session)
            responders = [
                candidate_responder
                for candidate_responder in responders
                if candidate_responder.user_id != message_sender.user_id
            ]
            if responders:

                responder = responders.pop()

                tracking_data = TrackingData(
                    conversation_id=conversation.conversation_id,
                    flow=IntentionName.ask_question,
                )
                question = get_question(self.session, conversation.question_id)

                viber_message = MessageBuilder.build_viber_message(
                    message_text=QUESTION_PREFIX + question.question_text,
                    tracking_data=asdict(tracking_data),
                )

                MessageSenger.send_viber_messagess(
                    viber=self.viber,
                    recipient_viber_id=responder.viber_id,
                    viber_message=viber_message,
                )
                conversation = update_conversation(
                    self.session,
                    conversation_id=conversation.conversation_id,
                    responder_user_id=responder.user_id,
                )

            else:
                conversation = update_conversation(
                    self.session,
                    conversation_id=conversation.conversation_id,
                    status=ConversationStatus.pending,
                    reset_responder_and_answer=True,
                )

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

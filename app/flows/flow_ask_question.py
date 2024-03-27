from dataclasses import asdict
from typing import Tuple
from app.data_classes import ConversationStatus, IntentionName, TrackingData
from app.flows.constants import QUESTION_PREFIX
from app.message_utils import MessageBuilder, MessageSenger
from app.data_models import (
    ChatBotUser,
    Conversation,
    Question,
    create_new_conversation,
    get_user_by_viber_id,
    get_users_not_in_active_pending_conversations,
)


def get_asker(session, viber_id) -> ChatBotUser:
    asker = get_user_by_viber_id(session=session, viber_id=viber_id)
    return asker


def select_responder(session, asker: ChatBotUser) -> ChatBotUser:
    responders = get_users_not_in_active_pending_conversations(session)
    responder = next(
        (responder for responder in responders if responder.user_id != asker.user_id),
        None,
    )
    return responder


def initiate_conversation(
    session, asker: ChatBotUser, responder: ChatBotUser, question: Question
) -> Tuple[Conversation, bool]:
    status = (
        ConversationStatus.pending if responder is None else ConversationStatus.active
    )
    conversation = create_new_conversation(
        session=session,
        question_id=question.question_id,
        responder_user_id=responder.user_id if responder else None,
        asker_user_id=asker.user_id,
        status=status,
    )
    return conversation, responder is not None


def send_question_to_responder(
    viber, responder: ChatBotUser, conversation: Conversation, question: Question
) -> None:
    tracking_data = TrackingData(
        conversation_id=conversation.conversation_id,
        flow=IntentionName.ask_question,
    )

    viber_message = MessageBuilder.build_viber_message(
        message_text=QUESTION_PREFIX + question.question_text,
        tracking_data=asdict(tracking_data),
    )

    MessageSenger.send_viber_messagess(
        viber=viber,
        recipient_viber_id=responder.viber_id,
        viber_message=viber_message,
    )

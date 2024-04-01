from dataclasses import asdict
from app.data_classes import ConversationStatus, IntentionName, TrackingData
from app.data_models import (
    ChatBotUser,
    Conversation,
    get_question,
    get_users_not_in_active_pending_conversations,
    update_answer,
    update_conversation,
)
from app.flows.constants import QUESTION_PREFIX
from app.message_utils import MessageBuilder, MessageSenger


def approve_answer_and_close_conversation(session, conversation: Conversation):
    update_answer(session, conversation.answer_id, approved=True)
    conversation = update_conversation(
        session,
        conversation_id=conversation.conversation_id,
        status=ConversationStatus.closed,
    )


def assign_responder_and_send_question(
    session, viber, responder: ChatBotUser, conversation: Conversation
):
    tracking_data = TrackingData(
        conversation_id=conversation.conversation_id,
        flow=IntentionName.ask_question,
    )
    question = get_question(session, conversation.question_id)

    viber_message = MessageBuilder.build_viber_message(
        message_text=QUESTION_PREFIX + question.question_text,
        tracking_data=asdict(tracking_data),
    )

    MessageSenger.send_viber_messagess(
        viber=viber,
        recipient_viber_id=responder.viber_id,
        viber_message=viber_message,
    )
    conversation = update_conversation(
        session,
        conversation_id=conversation.conversation_id,
        responder_user_id=responder.user_id,
    )


def handle_reject_response(
    session, viber, conversation: Conversation, message_sender: ChatBotUser
):
    responders = get_users_not_in_active_pending_conversations(session)
    responders = [
        candidate_responder
        for candidate_responder in responders
        if candidate_responder.user_id != message_sender.user_id
    ]
    if responders:
        assign_responder_and_send_question(
            session, viber, responder=responders.pop(), conversation=conversation
        )

    else:
        conversation = update_conversation(
            session,
            conversation_id=conversation.conversation_id,
            status=ConversationStatus.pending,
            reset_responder_and_answer=True,
        )

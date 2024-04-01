from dataclasses import asdict
from app.data_classes import (
    ConversationStatus,
    IntentionName,
    TrackingData,
    ViberMessage,
)
from app.data_models import (
    ChatBotUser,
    Conversation,
    create_answer,
    get_answer,
    get_user_by_user_id,
    update_answer,
    update_conversation,
)
from app.flows.constants import ANSWER_PREFIX
from app.message_utils import MessageBuilder, MessageSenger


def create_answer_and_update_conversation(
    session, viber_message: ViberMessage, conversation: Conversation
):
    answer = create_answer(
        session,
        viber_message.message_text,
        conversation.question_id,
        conversation.responder_user_id,
    )
    conversation = update_conversation(
        session=session,
        conversation_id=conversation.conversation_id,
        answer_id=answer.answer_id,
        status=ConversationStatus.active,
    )


def append_answer_text_to_existing_answer(
    session, viber_message: ViberMessage, conversation: Conversation
):
    answer = get_answer(session, conversation.answer_id)
    updated_answer_text = answer.answer_text + "\n " + viber_message.message_text
    answer = update_answer(session, answer.answer_id, answer_text=updated_answer_text)


def send_answer_acceptance_message(
    session, viber, conversation: Conversation, asker: ChatBotUser
):
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
        viber,
        recipient_viber_id=asker.viber_id,
        viber_message=answer_acceptance_message,
    )

    conversation = update_conversation(
        session=session,
        conversation_id=conversation.conversation_id,
        status=ConversationStatus.waiting_for_approval,
    )


def finalize_and_send_answer(session, viber, conversation: Conversation):
    answer = get_answer(session, conversation.answer_id)
    message_text = ANSWER_PREFIX + answer.answer_text
    tracking_data = TrackingData(
        conversation_id=conversation.conversation_id,
        system_message=False,
        flow=IntentionName.answer_question,
    )

    answer_message = MessageBuilder.build_viber_message(
        message_text=message_text, tracking_data=asdict(tracking_data)
    )

    asker = get_user_by_user_id(session=session, user_id=conversation.asker_user_id)

    MessageSenger.send_viber_messagess(
        viber,
        recipient_viber_id=asker.viber_id,
        viber_message=answer_message,
    )

    send_answer_acceptance_message(session, viber, conversation, asker)


def handle_responder_answer(
    session, viber, conversation: Conversation, viber_message: ViberMessage
):
    if conversation.answer_id is None:
        create_answer_and_update_conversation(session, viber_message, conversation)

    elif (conversation.answer_id is not None) and (
        viber_message.message_text.lower().strip() != "xxx"
    ):
        append_answer_text_to_existing_answer(session, viber_message, conversation)
    elif (conversation.answer_id is not None) and (
        viber_message.message_text.lower().strip() == "xxx"
    ):
        finalize_and_send_answer(session, viber, conversation)

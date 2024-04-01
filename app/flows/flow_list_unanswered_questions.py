from dataclasses import asdict
from app.data_classes import IntentionName, TrackingData, ViberMessage
from app.data_models import get_questions_without_approved_answers
from app.flows.constants import UNANSWERED_QUESTIONS_PREFIX
from app.message_utils import MessageBuilder, MessageSenger


def get_and_send_unanswered_questions(session, viber, viber_message: ViberMessage):
    unanswered_questions = get_questions_without_approved_answers(session)
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
        viber=viber,
        recipient_viber_id=viber_message.sender_viber_id,
        viber_message=viber_message,
    )

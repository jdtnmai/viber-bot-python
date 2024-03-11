from app.postgre_entities import (
    ChatBotUser,
    Question,
    Answer,
    Session,
    create_question,
    create_answer,
)
from sqlalchemy import and_, not_


def get_user_by_viber_id(session, viber_id):
    return (
        session.query(ChatBotUser)
        .filter(and_(ChatBotUser.active == True, ChatBotUser.viber_id == viber_id))
        .first()
    )


def get_all_users_except_excluded(session, excluded_user_ids: list):
    return (
        session.query(ChatBotUser)
        .filter(
            and_(
                ChatBotUser.active == True,
                not_(ChatBotUser.user_id.in_(excluded_user_ids)),
            )
        )
        .all()
    )


def parse_message(sender_viber_id, message_dict):
    session = Session()
    sender = get_user_by_viber_id(session, sender_viber_id)
    message_text = message_dict["text"]

    if message_text.lower().startswith("klausi"):
        question = create_question(session, message_text, sender.user_id)
        new_text = f"Prašau atsakyti į klausimą :) {message_text}"
        tracking_data = question.to_json()
        recipients_list = get_all_users_except_excluded(session, [sender.user_id])

        session.close()
        return dict(text=new_text, tracking_data=tracking_data), recipients_list

    else:
        session.close()
        return ({"text": "ne klausimas", "tracking_data": "nothing to track"}, [sender])

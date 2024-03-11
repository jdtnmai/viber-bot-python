import json
from app.postgre_entities import (
    ChatBotUser,
    Question,
    Answer,
    Session,
    create_question,
    create_answer,
)
from sqlalchemy import and_, not_

import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def get_user_by_viber_id(session, viber_id):
    return (
        session.query(ChatBotUser)
        .filter(and_(ChatBotUser.active == True, ChatBotUser.viber_id == viber_id))
        .first()
    )


def get_user_by_user_id(session, user_id):
    return (
        session.query(ChatBotUser)
        .filter(and_(ChatBotUser.active == True, ChatBotUser.user_id == user_id))
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
        return (dict(text=new_text, tracking_data=tracking_data), recipients_list)
    elif "tracking_data" in message_dict:
        tracking_data = json.loads(message_dict["tracking_data"])
        question_id, asked_user_id = (
            tracking_data["question_id"],
            tracking_data["user_id"],
        )
        logger.debug(f"parsed tracking data {question_id, asked_user_id}")
        answer = create_answer(session, message_text, question_id, sender.user_id)
        asked_user = get_user_by_user_id(session, asked_user_id)
        logger.debug(f"anwer response values : {answer.to_json()}, {asked_user}")
        return (
            dict(
                text=f"Gavote atsakyma. {answer.answer_text}",
                tracking_data=tracking_data,
            ),
            [asked_user],
        )
    else:
        session.close()
        return ({"text": "ne klausimas", "tracking_data": "nothing to track"}, [sender])

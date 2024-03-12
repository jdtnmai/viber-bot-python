import json
from app.postgre_entities import (
    ChatBotUser,
    Question,
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


def get_unanswered_questions(session):
    return session.query(Question).filter(~Question.answers.any()).all()


## Parse message
"""
1. get sender object
2. get message intention
    - question
    - answer 
    - has text? 
    - has url? 
    - has image? 
3. parse tracking data json string
"""


def parse_tracking_data(message_dict):
    logger.debug("parsing tracking data", message_dict)
    if "tracking_data" in message_dict.keys():
        tracking_data_json = message_dict["tracking_data"]
    else:
        tracking_data_json = "{}"

    tracking_data = json.loads(tracking_data_json)
    logger.debug("dictionary returned tracking data", tracking_data)
    return tracking_data


def get_chat_bot_intention(message_dict):

    text = message_dict.get("text").lower()
    asking_question = text.startswith("klausimas")
    asking_to_list_unanswered_questions = text.startswith("neatsakyti klausimai")

    return dict(
        asking_question=asking_question,
        asking_to_list_unanswered_questions=asking_to_list_unanswered_questions,
    )


def get_message_media(message_dict):
    media_link = message_dict.get("media", "")
    return media_link


def parse_message(session, sender_viber_id, message_dict):
    intention = get_chat_bot_intention(message_dict)

    sender = get_user_by_viber_id(session, sender_viber_id)
    tracking_data = parse_tracking_data(message_dict)

    media_link = get_message_media(message_dict)
    message_text = message_dict["text"]

    if intention["asking_question"]:  # "klausimas"
        question = create_question(session, message_text, sender.user_id)

        new_text = f"Prašau atsakyti į klausimą :) {message_text}"

        messages_out = [dict(text=new_text, tracking_data=question.to_json())]

        recipients_list = get_all_users_except_excluded(session, [sender.user_id])

        return (
            messages_out,
            recipients_list,
        )

    elif intention["asking_to_list_unanswered_questions"]:  # "neatsakyti klausimai"
        questions = get_unanswered_questions(session)

        messages_out = [
            {
                "text": f"{question.question_id}. {question.question_text}",
                "tracking_data": json.dumps(
                    {"intention": "manual_answer", "question_id": question.question_id}
                ),
            }
            for question in questions
        ]
        recipient_list = [sender]
        return (
            messages_out,
            recipient_list,
        )

    # if message_text.lower().startswith("klausi"):
    #     question = create_question(session, message_text, sender.user_id)
    #     new_text = f"Prašau atsakyti į klausimą :) {message_text}"
    #     recipients_list = get_all_users_except_excluded(session, [sender.user_id])

    #     return (dict(text=new_text, tracking_data=question.to_json()), recipients_list)
    # elif "tracking_data" in message_dict:
    #     tracking_data = json.loads(message_dict["tracking_data"])
    #     question_id, asked_user_id = (
    #         tracking_data["question_id"],
    #         tracking_data["user_id"],
    #     )
    #     logger.debug(f"parsed tracking data {question_id, asked_user_id}")
    #     print(f"parsed tracking data {question_id, asked_user_id}")
    #     answer = create_answer(session, message_text, question_id, sender.user_id)
    #     asked_user = get_user_by_user_id(session, asked_user_id)
    #     logger.debug(f"answer response values : {answer.to_json()}, {asked_user}")
    #     return (
    #         dict(
    #             text=f"Gavote atsakyma. {answer.answer_text}",
    #             tracking_data=answer.to_json(),
    #         ),
    #         [asked_user],
    #     )
    else:
        return (
            [
                {
                    "text": "ne klausimas",
                    "tracking_data": json.dumps(
                        {"tracking_message": "nothing to track"}
                    ),
                }
            ],
            [sender],
        )

import json
from app.postgre_entities import (
    ChatBotUser,
    Question,
    create_question,
    create_answer,
)
from sqlalchemy import and_, not_

from logger import logger

from app.conversation_tracker import conversation_manager

logger.debug("entered viber_chat_bot_logic")


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
    return session.query(Question).filter(~Question.answer.any()).all()


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


def review_message_statuses(conversation_manager):
    logger.debug("reviewed message statuses")


def parse_json(json_string):
    try:
        parsed_string = json.loads(json_string)
    except json.JSONDecodeError as e:
        parsed_string = {}
    return parsed_string


def parse_tracking_data(message_dict):
    logger.debug("parsing tracking data", message_dict)
    logger.debug(
        f"parsing tracking data message_dict keys { message_dict.keys()}, {type(message_dict)}"
    )

    if "tracking_data" in message_dict.keys():
        tracking_data_json = message_dict["tracking_data"]
        tracking_data = parse_json(tracking_data_json)
        logger.debug(f"raw tracking data {tracking_data_json}")
        logger.debug(f"parsed tracking data {tracking_data}")
        return tracking_data

    return {}


def get_chat_bot_intention(message_dict):

    text = message_dict.get("text").lower()
    asking_question = text.startswith("klausimas")
    asking_to_list_unanswered_questions = text.startswith("neatsakyti klausimai")
    welcome_with_help = text.startswith("labas")

    return dict(
        asking_question=asking_question,
        asking_to_list_unanswered_questions=asking_to_list_unanswered_questions,
        welcome_with_help=welcome_with_help,
    )


def get_message_media(message_dict):
    media_link = message_dict.get("media", "")
    return media_link


def parse_message(session, sender_viber_id, message_dict):
    logger.debug("Checking messages statuses before parsing a message")
    review_message_statuses(conversation_manager)

    logger.debug("entered parse_message")
    logger.debug(f"message_dict {message_dict}")
    intention = get_chat_bot_intention(message_dict)
    logger
    sender = get_user_by_viber_id(session, sender_viber_id)
    tracking_data = parse_tracking_data(message_dict)

    media_link = get_message_media(message_dict)
    message_text = message_dict["text"]
    logger.debug(f"intentions {intention}")
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
    elif intention["welcome_with_help"]:
        welcome_help_message = {
            "text": "Labas! Aš esu FoxBot. Mano darbas padėti atsakyti į Jūsų užduotus klausimus. Jeigu nežinosiu atsakymo, tada paklausiu Jūsų kolegų. \n\
                Komandos:\n\
                1. labas - pamatysite šią žinutę,\n\
                2. klausimas: <klausimo tekstas>? - užduosite man klausimą,\n\
                3. neatsakyti klausimai - pamatysi visus klausimus, kurie neturi atsakymo,\n\
                4. atsakyti <klausimo nr> - atsakyti, neatsakytą klausimą,\n\
                5. xxx - atsakymo pabaigos ženklas. Jeigu pabaigėte atsakymą, išsiųskite šią žinutę,\n\
                6. tvirtinu - jeigu į gautą atsakymą atasakysite šia komnada, kai kitą kartą klausite to pačio klausimo, gausite patvirtintą atsakymą.\n\n\
        SVARBU: Jeigu aš jums uždaviau klausimą, į jį pradėkite atskainėti nauja žinutę.\n\
                Atsakymą gali sudaryti daugiau nei viena žinutė.\n\
                Pabaigus atsakymą atsiųskite žinutę xxx",
            "tracking_data": json.dumps({"tracking_message": "nothing to track"}),
        }
        messages_out = [welcome_help_message]
        recipient_list = [sender]
        return (
            messages_out,
            recipient_list,
        )

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

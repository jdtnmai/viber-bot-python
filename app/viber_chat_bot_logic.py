import json
import time
from app.postgre_entities import (
    ChatBotUser,
    Question,
    answer_exists,
    create_question,
    create_answer,
    get_answer,
    get_question,
    get_user_answer,
    update_answer,
)
from sqlalchemy import and_, not_

from logger import logger

from app.conversation_tracker import (
    CSAttributes,
    Status,
    ConversationManager,
    ConversationStatus,
)


def create_conversation(conversation_manager, sender_id, question_id):
    conversation_id = conversation_manager.get_next_conversation_id()
    conversation = ConversationStatus(
        conversation_id=conversation_id,
        sender_id=sender_id,
        question_id=question_id,
    )

    conversation_manager.add_conversation(conversation_id, conversation)
    return conversation_id


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


def ask_question(conversation_manager, session, message_text, sender):
    question = create_question(session, message_text, sender.user_id)

    conversation_id = create_conversation(
        conversation_manager,
        sender.user_id,
        question.question_id,
    )

    conversation_manager.update_conversation(
        conversation_id=conversation_id,
        updated_attributes={CSAttributes.status: Status.sender_asked_question},
    )
    logger.debug(
        f"conversation_manager conversation {conversation_manager.conversations}"
    )
    logger.debug(f"conversation statuses: {conversation_manager.conversations}")

    # From here down we must refactor to decouple message sending operation.
    return conversation_id


def get_question_answer():
    return "...|..."


def does_question_have_answer(answer_candidate):
    return False


def asking_question_flow(conversation_manager, session, message_text, sender):
    conversation_id = ask_question(session, message_text, sender)
    tracking_data = {"conversation_id": conversation_id}

    answer_candidate = get_question_answer()
    question_has_anwer = does_question_have_answer(answer_candidate)
    question_does_not_have_answer = not question_has_anwer
    if question_has_anwer:
        recipients_list = [sender.user_id]
        messages_out = [
            dict(
                text=answer_candidate,
                tracking_data=json.dumps(tracking_data),
            )
        ]
        send_message = True
        conversation_manager.update_conversation(
            conversation_id=conversation_id,
            updated_attributes={CSAttributes.status: Status.conversation_finished},
        )
        logger.debug(f"conversation statuses: {conversation_manager.conversations}")
        return messages_out, recipients_list, send_message

    if question_does_not_have_answer:
        recipients_list = get_all_users_except_excluded(session, [sender.user_id])
        responders_list = [user.user_id for user in recipients_list]
        responder_id = responders_list.pop() if responders_list else None

        conversation_manager.update_conversation(
            conversation_id=conversation_id,
            updated_attributes={
                CSAttributes.active_responder_id: responder_id,
                CSAttributes.responders: responders_list,
                CSAttributes.status: Status.sent_question_to_responder,
            },
        )
        logger.debug(f"conversation statuses: {conversation_manager.conversations}")
        new_text = f"Prašau atsakyti į klausimą :) {message_text}"

        messages_out = [
            dict(
                text=new_text,
                tracking_data=json.dumps(tracking_data),
            )
        ]
        recipients_list
        send_message = True
        return messages_out, recipients_list, send_message


def conversation_flow(
    session,
    conversation_id,
    sender,
    message_text,
    media_link,
):
    """
    sender_started_conversation = "sender_started_conversation"
    sender_asked_question = "sender_asked_question"
    sent_question_to_responder = "sent_question_to_responder"
    responder_writes_answer = "responder_writes_answer"
    responder_submitted_answer = "responder_submitted_answer"
    sender_accepted_answer = "sender_accepted_answer"
    sender_rejected_answer = "sender_rejected_answer"
    conversation_finished = "conversation_finished"
    """

    conversation = conversation_manager.get_conversation(
        conversation_id=conversation_id
    )
    conversation_status = conversation.status

    if conversation_status == Status.sent_question_to_responder:
        """
        if status is sent q to responder, it means that we probably got back an answer.
        we create answer object, add answer and update status, message recieved time.  dont send message
        """
        exists = answer_exists(
            session, conversation.active_responder_id, conversation.question_id
        )
        if not exists:
            answer = create_answer(
                session,
                message_text,
                conversation.question_id,
                conversation.active_responder_id,
            )

            conversation_manager.update_conversation(
                conversation_id=conversation_id,
                updated_attributes={
                    CSAttributes.last_message_time: time.time(),
                    CSAttributes.conversation_status: Status.responder_writes_answer,
                },
            )
            send_message = False
            return (
                [],
                [],
                send_message,
            )

    if conversation_status == Status.responder_writes_answer:
        """
        if status is responder write answer, we check if message is xxx, if yes, we update status, message time and send a message to the question owner.
        if message is not xxx, we append the answer and update message time. dont send message
        """
        exists = answer_exists(
            session, conversation.responder_id, conversation.question_id
        )
        if exists:
            if message_text == "xxx":
                answer = get_user_answer(
                    session, conversation.responder_id, conversation.question_id
                )
                conversation_manager.update_conversation(
                    conversation_id=conversation_id,
                    updated_attributes={
                        CSAttributes.last_message_time: time.time(),
                        CSAttributes.status: Status.responder_submitted_answer,
                    },
                )
                recipients = [
                    get_user_by_user_id(getattr(conversation, CSAttributes.sender_id))
                ]
                messages = [
                    {
                        "message_text": answer.answer_text,
                        "tracking_data": json.dumps(
                            {"conversation_id": conversation_id}
                        ),
                    }
                ]
                send_message = True
                return (recipients, messages, send_message)
            elif message_text != "xxx":
                answer = get_user_answer(
                    session, conversation.responder_id, conversation.question_id
                )
                updated_answer = f"{answer.answer_text}\n {message_text}"

                update_answer(session, answer.answer_id, answer_text=updated_answer)

                conversation_manager.update_conversation(
                    conversation_id=conversation_id,
                    updated_attributes={
                        CSAttributes.last_message_time: time.time(),
                    },
                )
                send_message = False
                return (
                    [],
                    [],
                    send_message,
                )

    if (conversation_status == Status.responder_submitted_answer) and (
        sender.user_id == conversation.sender_id
    ):
        if message_text.lower() == "taip":
            """
            atsakymas priimtas.
            klausimas tampa approved.
            conversation status pasikeicia i finished.
            atnaujinam zinutes laika
            """
            conversation_manager.update_conversation(
                conversation_id=conversation_id,
                updated_attributes={
                    CSAttributes.last_message_time: time.time(),
                    CSAttributes.status: Status.sender_accepted_answer,
                },
            )

            answer = get_user_answer(
                session, conversation.responder_id, conversation.question_id
            )

            recipients = [
                get_user_by_user_id(getattr(conversation, CSAttributes.sender_id))
            ]
            messages = [
                {
                    "message_text": answer.answer_text,
                    "tracking_data": json.dumps({"conversation_id": conversation_id}),
                }
            ]
            send_message = True
            return (
                [],
                [],
                send_message,
            )

        if message_text.lower() == "ne":
            """
            atsakymas atmestas.
            conversation status pasikeicia i rejected.
            atnaujinam zinutes laika
            perziurim ar yra responderiu. jeigu yra paimam pirma ir siunciam jam. Pakeiciam statusa i sent to responder.
            reikia patikrinti, ar responder neturi aktyviu klausimu ir atsakymu. is respnder available?
            """
            conversation_manager.update_conversation(
                conversation_id=conversation_id,
                updated_attributes={
                    CSAttributes.last_message_time: time.time(),
                    CSAttributes.status: Status.sender_rejected_answer,
                },
            )
            responder_id = None
            for _responder_id in conversation.responder_list:
                if conversation_manager.is_user_available(_responder_id):
                    responder_id = _responder_id
                    break
            if responder_id is not None:
                conversation.responder_list.remove(responder_id)
                conversation_manager.update_conversation(
                    conversation_id=conversation_id,
                    updated_attributes={
                        CSAttributes.active_responder_id: responder_id,
                        CSAttributes.status: Status.sent_question_to_responder,
                        CSAttributes.last_message_time: time.time(),
                    },
                )
                question = get_question(session, conversation.question_id)
                recipients = [get_user_by_user_id(responder_id)]
                messages = [
                    {
                        "message_text": f"Prašau atsakyti į klausimą :) {question.question_text}",
                        "tracking_data": json.dumps(
                            {"conversation_id": conversation_id}
                        ),
                    }
                ]
                send_message = True
                return (
                    recipients,
                    messages,
                    send_message,
                )
            if responder_id is None:
                send_message = False
                return (
                    [],
                    [],
                    send_message,
                )


def parse_message(session, sender_viber_id, message_dict):
    conversation_manager = ConversationManager()
    logger.debug(f"incoming_message_text {message_dict['text']}")
    logger.debug(f"parse message conversation_manager_id {id(conversation_manager)}")
    logger.debug("Checking messages statuses before parsing a message")
    review_message_statuses(conversation_manager)

    logger.debug("entered parse_message")
    logger.debug(f"message_dict {message_dict}")

    sender = get_user_by_viber_id(session, sender_viber_id)
    intention = get_chat_bot_intention(message_dict)

    media_link = get_message_media(message_dict)
    message_text = message_dict["text"]

    tracking_data = parse_tracking_data(message_dict)
    logger.debug(f"tracking_data {tracking_data}")
    logger.debug(
        f"conversation_manager conversation {conversation_manager.conversations}"
    )
    if "conversation_id" not in tracking_data:
        conversation_id = None
        conversation_status = None
    else:

        conversation_id = tracking_data.get("conversation_id")
        conversation_status = conversation_manager.get_conversation_status(
            conversation_id
        )
        logger.debug(
            f"conversation_id {conversation_id}, {conversation_manager.conversations}"
        )

    logger.debug(
        f"is conversation flow {any(intention.values())}, conversation_status {conversation_status}, if evaluation {not any(intention.values()) and conversation_status is not None}"
    )
    if not any(intention.values()) and conversation_status is not None:
        messages_out, recipients_list, send_message = conversation_flow(
            session,
            conversation_id,
            sender,
            message_text,
            media_link,
        )

        return (
            messages_out,
            recipients_list,
            send_message,
        )

    logger.debug(f"intentions {intention}")
    if intention["asking_question"]:  # "klausimas"
        messages_out, recipients_list, send_message = asking_question_flow(
            conversation_manager, session, message_text, sender
        )
        return (
            messages_out,
            recipients_list,
            send_message,
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
            True,
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
            True,
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
            True,
        )

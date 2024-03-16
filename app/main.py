from flask import Flask, render_template, request, Response, send_file
from sqlalchemy import inspect
from sqlalchemy.orm import aliased
from app.flow_manager import FlowManager
from app.message_utils import MessageBuilder, MessageSenger
from app.postgre_entities import ChatBotUser, Question, Answer
from app.postgre_entities import Session
from app.viber_chat_bot_logic import parse_message, review_message_statuses
from app.conversation_tracker import ConversationManager

from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.viber_requests import ViberConversationStartedRequest
from viberbot.api.viber_requests import ViberFailedRequest
from viberbot.api.viber_requests import ViberMessageRequest
from viberbot.api.viber_requests import ViberSubscribedRequest
from viberbot.api.viber_requests import ViberUnsubscribedRequest

import sched
import time
import threading


import os

from logger import logger

app = Flask(__name__)


# Define your ConversationManager class and functions here


def conversation_manager_review(conversation_manager):
    logger.debug("Checking meesage status via conversation_manager_review every 60s. ")
    review_message_statuses(conversation_manager)


viber = Api(
    BotConfiguration(
        name="FoxBot",
        avatar="https://viber-fox-bot-9d12996926ae.herokuapp.com/foxbot_face",
        auth_token=os.environ["VIBER_AUTH_KEY"],
    )
)


def set_webhook(viber):
    viber.set_webhook("https://viber-fox-bot-9d12996926ae.herokuapp.com/")


# Schedule conversation manager review
scheduler = sched.scheduler(time.time, time.sleep)
scheduler.enter(5, 1, set_webhook, (viber,))
# scheduler.enter(60, 1, conversation_manager_review, (conversation_manager,))
t = threading.Thread(target=scheduler.run)
t.start()


scheduler2 = sched.scheduler(time.time, time.sleep)
# scheduler2.enter(5, 1, set_webhook, (viber,))
conversation_manager = ConversationManager()
logger.debug(f"main function conversation_manager_id {id(conversation_manager)}")
scheduler2.enter(60, 1, conversation_manager_review, (conversation_manager,))
t2 = threading.Thread(target=scheduler2.run)
t2.start()


@app.route("/", methods=["GET"])
def hello_world():
    logger.debug("called hello world")
    return render_template("index_template.html")


@app.route("/chatbot_users", methods=["GET"])
def display_chat_bot_users():
    session = Session()
    users = session.query(ChatBotUser).all()

    mapper = inspect(ChatBotUser)

    users_simple_types = [
        {key: getattr(user_instance, key) for key in mapper.attrs.keys()}
        for user_instance in users
    ]
    session.close()
    return render_template("json_template.html", json_data=users_simple_types)


@app.route("/questions", methods=["GET"])
def display_questions():
    session = Session()

    questions = session.query(Question).all()
    mapper = inspect(Question)

    questions_simple_types = [
        {key: getattr(question_instance, key) for key in mapper.attrs.keys()}
        for question_instance in questions
    ]

    session.close()
    return render_template("json_template.html", json_data=questions_simple_types)


@app.route("/answers", methods=["GET"])
def display_answers():
    session = Session()

    answers = session.query(Answer).all()
    mapper = inspect(Answer)

    answers_simple_types = [
        {key: getattr(answer_instance, key) for key in mapper.attrs.keys()}
        for answer_instance in answers
    ]
    return render_template("json_template.html", json_data=answers_simple_types)


@app.route("/q_and_a", methods=["GET"])
def display_q_and_a():
    session = Session()
    question_user_alias = aliased(ChatBotUser)

    answer_user_alias = aliased(ChatBotUser)

    # Query for questions and approved answers
    questions_and_answers = (
        session.query(Question, Answer, question_user_alias, answer_user_alias)
        .join(Answer, Question.question_id == Answer.question_id)
        .join(question_user_alias, Question.user_id == question_user_alias.user_id)
        .join(answer_user_alias, Answer.user_id == answer_user_alias.user_id)
        .filter(Answer.approved == True)
        .all()
    )

    # Process results
    result = []
    for question, answer, question_user, answer_user in questions_and_answers:
        result.append(
            {
                "question_user_name": question_user.name,
                "question_text": question.question_text,
                "answer_user_name": answer_user.name,
                "answer_text": answer.answer_text,
            }
        )
    session.close()
    return render_template("json_template.html", json_data=result)


@app.route("/foxbot_face")
def show_foxbot_face():
    # Imagine that user_image is determined dynamically for each user
    face_path = "static/images/resized_foxbot_image.png"
    return send_file(face_path, mimetype="image/png")


@app.route("/", methods=["POST"])
def incoming():
    session = Session()
    if isinstance(viber_request, ViberMessageRequest):
        viber_request = viber.parse_request(request.get_data().decode("utf8"))
        fm = FlowManager(session, viber, viber_request)
        fm.execute_flow()

    elif (
        isinstance(viber_request, ViberConversationStartedRequest)
        or isinstance(viber_request, ViberSubscribedRequest)
        or isinstance(viber_request, ViberUnsubscribedRequest)
    ):
        viber.send_messages(
            viber_request.user.id,
            [TextMessage(None, None, viber_request.event_type)],
        )
    elif isinstance(viber_request, ViberFailedRequest):
        logger.warn(
            "client failed receiving message. failure: {0}".format(viber_request)
        )

    session.close()
    return Response(status=200)

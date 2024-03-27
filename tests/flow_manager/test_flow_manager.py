from dataclasses import asdict
from datetime import datetime
import pytest
from unittest.mock import ANY, Mock, call

from app.data_classes import ViberMessage
from app.flow_manager import FlowManager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.postgre_entities import Answer, Base, ChatBotUser, Conversation, Question


import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FoxBotTestLogs")


def model_to_dict(instance, session):
    from sqlalchemy.inspection import inspect

    instance_data = {}
    for attr in inspect(instance).attrs:
        value = getattr(instance, attr.key)
        # Convert datetime to string
        if isinstance(value, datetime):
            instance_data[attr.key] = value.isoformat()
        # Handle relationships
        elif hasattr(attr, "relationship") and value is not None:
            if attr.relationship.uselist:  # For one-to-many relationships
                instance_data[attr.key] = [model_to_dict(i, session) for i in value]
            else:  # For one-to-one relationships
                instance_data[attr.key] = model_to_dict(value, session)
        else:
            instance_data[attr.key] = value
    return instance_data


@pytest.fixture
def test_session():
    # Create an in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:", echo=True, future=True)
    Base.metadata.create_all(engine)  # Create tables
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session: Session = SessionLocal()
    yield session  # Use the session for testing
    session.close()
    Base.metadata.drop_all(engine)  # Clean up the database


@pytest.fixture
def setup_database_for_test_2_users(test_session: Session):
    # Create test users, including user_2 and potential responders
    user_asker = ChatBotUser(
        user_id=1, name="Asker User", viber_id="viber_user_1", active=True
    )
    user_responder = ChatBotUser(
        user_id=2, name="Responder User", viber_id="viber_user_2", active=True
    )
    test_session.add_all([user_asker, user_responder])
    test_session.commit()

    return user_asker, user_responder


@pytest.fixture
def setup_database_for_test_3_users(test_session: Session):
    # Create test users, including user_2 and potential responders
    user_1 = ChatBotUser(user_id=1, name="User 1", viber_id="viber_user_1", active=True)
    user_2 = ChatBotUser(user_id=2, name="User 2", viber_id="viber_user_2", active=True)
    user_3 = ChatBotUser(user_id=3, name="User 3", viber_id="viber_user_3", active=True)
    users = [user_1, user_2, user_3]

    test_session.add_all(users)
    test_session.commit()

    return users


@pytest.fixture
def mocked_viber_client():
    # Create a mock object for the Viber client
    mock = Mock()
    mock.send_messages.return_value = 777
    # Optionally, you can set return values or side effects for specific methods
    # mock.send_message.return_value = ...
    return mock


def call_flow_execution(viber_request_question, test_session, mocked_viber_client):
    flow_manager = FlowManager(
        session=test_session,
        viber=mocked_viber_client,
        viber_request=viber_request_question,
    )
    flow_manager.execute_flow()


def start_conversation_with_question(
    user_asker, user_responder, test_session, mocked_viber_client
):
    viber_request_question = ViberMessage(
        sender_viber_id=user_asker.viber_id,
        message_text="klausimas: testinis klausimas?",
        media_link="",
        tracking_data={},
    )

    call_flow_execution(viber_request_question, test_session, mocked_viber_client)


def reply_to_the_question(
    user_asker, user_responder, test_session, mocked_viber_client
):

    viber_request_question = ViberMessage(
        sender_viber_id=user_responder.viber_id,
        message_text="testinis atsakymas.",
        media_link="",
        tracking_data={
            "conversation_id": 1,
            "system_message": False,
            "flow": "klausimas",
        },
    )

    call_flow_execution(viber_request_question, test_session, mocked_viber_client)

    viber_request_question = ViberMessage(
        sender_viber_id=user_responder.viber_id,
        message_text="Atsakymo papildymas.",
        media_link="",
        tracking_data={
            "conversation_id": 1,
            "system_message": False,
            "flow": "klausimas",
        },
    )
    call_flow_execution(viber_request_question, test_session, mocked_viber_client)

    viber_request_question = ViberMessage(
        sender_viber_id=user_responder.viber_id,
        message_text="xxx",
        media_link="",
        tracking_data={
            "conversation_id": 1,
            "system_message": False,
            "flow": "klausimas",
        },
    )

    call_flow_execution(viber_request_question, test_session, mocked_viber_client)


def approve_answer(user_asker, user_responder, test_session, mocked_viber_client):
    viber_request_question = ViberMessage(
        sender_viber_id=user_asker.viber_id,
        message_text="taip",
        media_link="",
        tracking_data={
            "conversation_id": 1,
            "system_message": True,
            "flow": "klausimas",
        },
    )

    call_flow_execution(viber_request_question, test_session, mocked_viber_client)


def decline_answer(user_asker, user_responder, test_session, mocked_viber_client):
    viber_request_question = ViberMessage(
        sender_viber_id=user_asker.viber_id,
        message_text="ne",
        media_link="",
        tracking_data={
            "conversation_id": 1,
            "system_message": True,
            "flow": "klausimas",
        },
    )

    call_flow_execution(viber_request_question, test_session, mocked_viber_client)


def test_ask_question_accepted_answer_flow(
    test_session, setup_database_for_test_2_users, mocked_viber_client
):
    user_asker, user_responder = setup_database_for_test_2_users

    # step 1: start conversation
    start_conversation_with_question(
        user_asker, user_responder, test_session, mocked_viber_client
    )

    # step 2: reply to the question with 2 messages and finish conversation with xxx.
    reply_to_the_question(user_asker, user_responder, test_session, mocked_viber_client)

    # step 3: approve message
    approve_answer(user_asker, user_responder, test_session, mocked_viber_client)

    # step 4: calls count

    assert mocked_viber_client.send_messages.call_count == 3

    calls = [
        call("viber_user_2", ANY),
        call("viber_user_1", ANY),
        call("viber_user_1", ANY),
    ]
    mocked_viber_client.send_messages.assert_has_calls(calls, any_order=False)


def test_ask_question_declined_answer_flow(
    test_session, setup_database_for_test_2_users, mocked_viber_client
):
    user_asker, user_responder = setup_database_for_test_2_users

    # step 1: start conversation
    start_conversation_with_question(
        user_asker, user_responder, test_session, mocked_viber_client
    )

    question = (
        test_session.query(Question).filter_by(user_id=user_asker.user_id).first()
    )

    assert question is not None, "Answer should be created"
    assert (
        question.question_text == "klausimas: testinis klausimas?"
    ), "Question text mismatch"

    conversation = (
        test_session.query(Conversation)
        .filter_by(question_id=question.question_id)
        .first()
    )
    logger.info(f"Conversation {model_to_dict(conversation, test_session)}")
    assert conversation is not None, "Conversation should be created"
    assert conversation.asker_user_id == user_asker.user_id, "Asker user ID mismatch"
    assert (
        conversation.responder_user_id == user_responder.user_id
    ), "Responder user ID mismatch"

    # step 2: reply to the question with 2 messages and finish conversation with xxx.
    reply_to_the_question(user_asker, user_responder, test_session, mocked_viber_client)

    answer = (
        test_session.query(Answer).filter_by(user_id=user_responder.user_id).first()
    )

    logger.info(f"Answer {model_to_dict(answer, test_session)}")
    logger.info(f"answer_text |{answer.answer_text}|")
    assert answer is not None, "Answer should be created"
    assert (
        answer.answer_text
        == """testinis atsakymas.
 Atsakymo papildymas."""
    ), "Answer text mismatch"

    conversation = test_session.query(Conversation).filter_by(conversation_id=1).first()
    assert (
        conversation.status == "waiting_for_approval"
    ), "conversation status should be waiting_for_approval"

    # step 3: approve message
    decline_answer(user_asker, user_responder, test_session, mocked_viber_client)
    conversation = test_session.query(Conversation).filter_by(conversation_id=1).first()
    assert conversation.status == "pending", "conversation status should be pending"
    assert (
        conversation.responder_user_id is None
    ), "conversation responder_user_id should be None"

    # step 4: calls count

    assert mocked_viber_client.send_messages.call_count == 3

    calls = [
        call("viber_user_2", ANY),
        call("viber_user_1", ANY),
        call("viber_user_1", ANY),
    ]
    mocked_viber_client.send_messages.assert_has_calls(calls, any_order=False)

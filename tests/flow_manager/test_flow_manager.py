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


def test_flow_manager_sends_message(
    test_session, setup_database_for_test_2_users, mocked_viber_client
):
    user_asker, user_responder = setup_database_for_test_2_users

    # Prepare the ViberMessage
    viber_request_question = ViberMessage(
        sender_viber_id=user_asker.viber_id,
        message_text="klausimas: testinis klausimas?",
        media_link="",
        tracking_data={},
    )

    # Initialize FlowManager with mocked Viber client
    flow_manager = FlowManager(
        session=test_session,
        viber=mocked_viber_client,
        viber_request=viber_request_question,
    )

    # Execute the method that triggers a message send
    flow_manager.execute_flow()

    # Verify that the Viber client's send_message was called as expected

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

    flow_manager = FlowManager(
        session=test_session,
        viber=mocked_viber_client,
        viber_request=viber_request_question,
    )
    flow_manager.execute_flow()

    # create answer

    answer = (
        test_session.query(Answer).filter_by(user_id=user_responder.user_id).first()
    )

    logger.info(f"Answer {model_to_dict(answer, test_session)}")

    assert answer is not None, "Answer should be created"
    assert answer.answer_text == "testinis atsakymas.", "Answer text mismatch"

    # Execute the method that triggers a message send

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

    flow_manager = FlowManager(
        session=test_session,
        viber=mocked_viber_client,
        viber_request=viber_request_question,
    )

    # Execute the method that triggers a message send
    flow_manager.execute_flow()

    # finish answer creation
    conversation = test_session.query(Conversation).filter_by(conversation_id=1).first()
    conversation.status == "waiting_for_approval"

    # After the function under test has been called...
    # Check that the function was called exactly two times

    assert mocked_viber_client.send_messages.call_count == 3

    # To further assert that the last call (or a specific call) was made with certain arguments:

    # If you need to assert the arguments of all calls:
    calls = [
        call("viber_user_2", ANY),
        call("viber_user_1", ANY),
        call("viber_user_1", ANY),
    ]  # Adjust as per actual expected calls
    mocked_viber_client.send_messages.assert_has_calls(calls, any_order=False)

    # send the answer to the asker


def test_flow_manager_handles_answers(
    test_session, setup_database_for_test_2_users, mocked_viber_client
):
    user_asker, user_responder = setup_database_for_test_2_users

    logger.info(f"Created_conversation {model_to_dict(user_asker, test_session)}")
    logger.info(f"Created_conversation {model_to_dict(user_responder, test_session)}")

    # Prepare the viber_request_question as per the user's example
    viber_request_question = ViberMessage(
        sender_viber_id=user_asker.viber_id,
        message_text="klausimas: testinis klausimas?",
        media_link="",
        tracking_data={},
    )

    # Initialize FlowManager with the test session and mocked viber_request
    flow_manager = FlowManager(
        session=test_session,
        viber=mocked_viber_client,
        viber_request=viber_request_question,
    )

    # Execute the flow that handles the question
    flow_manager.execute_flow()

    # Verify a question and a conversation have been created
    question = (
        test_session.query(Question).filter_by(user_id=user_asker.user_id).first()
    )
    logger.info(f"Question {model_to_dict(question, test_session)}")
    assert question is not None, "Question should be created"
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

    # Depending on your FlowManager implementation, further verify that a responder has been selected
    # and that the appropriate actions (like sending a message) have been mocked and called as expected.

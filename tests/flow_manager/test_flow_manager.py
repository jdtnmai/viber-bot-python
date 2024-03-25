import pytest
from unittest.mock import ANY, Mock
from app.data_classes import ViberMessage
from app.flow_manager import FlowManager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.postgre_entities import Base, ChatBotUser, Conversation, Question


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
def setup_database_for_test(test_session: Session):
    # Create test users, including user_2 and potential responders
    user_asker = ChatBotUser(
        user_id=2, name="Asker User", viber_id="user_2", active=True
    )
    user_responder = ChatBotUser(
        user_id=3, name="Responder User", viber_id="responder_1", active=True
    )
    test_session.add_all([user_asker, user_responder])
    test_session.commit()

    return user_asker, user_responder


@pytest.fixture
def mocked_viber_client():
    # Create a mock object for the Viber client
    mock = Mock()
    mock.send_messages.return_value = 777
    # Optionally, you can set return values or side effects for specific methods
    # mock.send_message.return_value = ...
    return mock


def test_flow_manager_sends_message(
    test_session, setup_database_for_test, mocked_viber_client
):
    user_asker, user_responder = setup_database_for_test

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
    mocked_viber_client.send_messages.assert_called_once_with("responder_1", ANY)


def test_flow_manager_handles_question_correctly(
    test_session, setup_database_for_test, mocked_viber_client
):
    user_asker, user_responder = setup_database_for_test

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
    assert question is not None, "Question should be created"
    assert (
        question.question_text == "klausimas: testinis klausimas?"
    ), "Question text mismatch"

    conversation = (
        test_session.query(Conversation)
        .filter_by(question_id=question.question_id)
        .first()
    )
    assert conversation is not None, "Conversation should be created"
    assert conversation.asker_user_id == user_asker.user_id, "Asker user ID mismatch"

    # Depending on your FlowManager implementation, further verify that a responder has been selected
    # and that the appropriate actions (like sending a message) have been mocked and called as expected.

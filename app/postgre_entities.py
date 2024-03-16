import json
import os
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime


# Create the SQLAlchemy engine
engine = create_engine(os.environ["DATABASE_URL"])

Session = sessionmaker(bind=engine)

# Create a base class for declarative class definitions
Base = declarative_base()


# Define the ChatBotUser table
class ChatBotUser(Base):
    __tablename__ = "chat_bot_users"

    user_id = Column(Integer, primary_key=True)
    name = Column(String)
    viber_id = Column(String)
    created_at = Column(DateTime)
    active = Column(Boolean)


# Define the Question table
class Question(Base):
    __tablename__ = "questions"

    question_id = Column(Integer, primary_key=True)
    question_text = Column(String)
    user_id = Column(Integer, ForeignKey("chat_bot_users.user_id"))
    created_at = Column(DateTime)

    user = relationship("ChatBotUser")
    answer = relationship("Answer", back_populates="question")


# Define the Answer table
class Answer(Base):
    __tablename__ = "answers"

    answer_id = Column(Integer, primary_key=True)
    answer_text = Column(String)
    question_id = Column(Integer, ForeignKey("questions.question_id"))
    user_id = Column(Integer, ForeignKey("chat_bot_users.user_id"))
    created_at = Column(DateTime)
    approved = Column(Boolean)

    question = relationship("Question", back_populates="answer")
    user = relationship("ChatBotUser")
    conversation = relationship(
        "Conversation", back_populates="answer", uselist=False
    )  # Ensure one-to-one relation


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.question_id"))
    asker_user_id = Column(Integer, ForeignKey("chat_bot_users.user_id"))
    responder_user_id = Column(Integer, ForeignKey("chat_bot_users.user_id"))
    answer_id = Column(
        Integer, ForeignKey("answers.answer_id"), nullable=True
    )  # Link to the Answer table
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    status = Column(String)  # e.g., "pending", "answered", "closed"

    # Relationships
    question = relationship("Question")
    asker = relationship("ChatBotUser", foreign_keys=[asker_user_id])
    responder = relationship("ChatBotUser", foreign_keys=[responder_user_id])
    answer = relationship(
        "Answer", back_populates="conversation"
    )  # Relationship to the Answer


def create_user(session, name, viber_id, active=True):
    user = ChatBotUser(
        name=name, viber_id=viber_id, created_at=datetime.now(), active=active
    )
    session.add(user)
    session.commit()
    return user


# Function to retrieve a ChatBotUser by user_id
def get_user(session, user_id):
    return session.get(ChatBotUser, user_id)


# Function to update a ChatBotUser's details
def update_user(session, user_id, name=None, viber_id=None, active=None):
    user = session.get(ChatBotUser, user_id)
    if user:
        if name:
            user.name = name
        if viber_id:
            user.viber_id = viber_id
        if active is not None:
            user.active = active
        session.commit()


# Function to delete a ChatBotUser
def delete_user(session, user_id):
    user = session.get(ChatBotUser, user_id)
    if user:
        session.delete(user)
        session.commit()


def create_question(session, question_text, user_id):
    question = Question(
        question_text=question_text, user_id=user_id, created_at=datetime.now()
    )
    session.add(question)
    session.commit()
    return question


# Function to retrieve a Question by question_id
def get_question(session, question_id):
    return session.get(Question, question_id)


# Function to update a Question's details
def update_question(session, question_id, question_text=None, user_id=None):
    question = session.get(Question, question_id)
    if question:
        if question_text:
            question.question_text = question_text
        if user_id:
            question.user_id = user_id
        session.commit()


# Function to delete a Question
def delete_question(session, question_id):
    question = session.get(Question, question_id)
    if question:
        session.delete(question)
        session.commit()


def create_answer(session, answer_text, question_id, user_id, approved=False):
    answer = Answer(
        answer_text=answer_text,
        question_id=question_id,
        user_id=user_id,
        created_at=datetime.now(),
        approved=approved,
    )
    session.add(answer)
    session.commit()
    return answer


def answer_exists(session, user_id, question_id):
    answer_exists = (
        session.query(Answer)
        .filter_by(question_id=question_id, user_id=user_id)
        .first()
    )
    if answer_exists is None:
        return False
    else:
        return True


def get_user_answer(session, user_id, question_id):
    answer = (
        session.query(Answer)
        .filter_by(question_id=question_id, user_id=user_id)
        .first()
    )
    return answer


# Function to retrieve an Answer by answer_id
def get_answer(session, answer_id):
    return session.get(Answer, answer_id)


# Function to update an Answer's details
def update_answer(session, answer_id, answer_text=None, user_id=None, approved=None):
    answer = session.get(Answer, answer_id)
    if answer:
        if answer_text:
            answer.answer_text = answer_text
        if user_id is not None:
            answer.user_id = user_id
        if approved is not None:
            answer.approved = approved
        session.commit()


# Function to delete an Answer
def delete_answer(session, answer_id):
    answer = session.query(Answer).get(answer_id)
    if answer:
        session.delete(answer)
        session.commit()


## main functions to work with data model


def create_tables(engine):
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    create_tables(engine)

    import random
    from faker import Faker

    fake = Faker()

    # Create a session
    session = Session()
    users = [
        create_user(session, name="BMW 3", viber_id=os.environ["viber_id_1"]),
        create_user(session, name="Ford Mustang", viber_id=os.environ["viber_id_2"]),
    ]

    # Generate 3 questions per user
    questions = []
    for user in users:
        for _ in range(2):
            question_text = fake.sentence()
            question = create_question(
                session, question_text=question_text, user_id=user.user_id
            )
            questions.append(question)

    # Generate 5 answers per user
    for user in users:
        for _ in range(2):
            answer_text = fake.text()
            question = random.choice(questions)
            answer = create_answer(
                session,
                answer_text=answer_text,
                question_id=question.question_id,
                user_id=user.user_id,
            )

    # Commit and close the session
    session.commit()
    session.close()

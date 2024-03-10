"""
We define main entities
1. user - A person that uses the chatbot. The person can ask/answer questions.
2. chatbot - a robot that accepts questions, searches for answers, post questions to the users and saves answered questions. 
    1. the chatbot adds uers to the the database, and iteracts with whitelisted users that are in the databse. 
"""

from dataclasses import dataclass

from mongo_utils import insert_document, collection_names


@dataclass
class User:
    user_name: str
    user_phone_number: str


@dataclass
class Question:
    question: str
    asked_by: str
    confirmed_by: str
    confirmed: bool = False


@dataclass
class Answer:
    answer: str
    answered_by: str
    question_id: str
    asked_by: str
    meta_link: str
    meta_image: str
    accepted: bool = False


def write_question_to_db(question: Question):
    documment_id = insert_document(
        document=question.asdict(), collection_name=collection_names.questions
    )
    return documment_id


def find_question_answer(quetion: Question) -> Any:
    return ...


def ask_question(question: Question):
    documment_id = write_question_to_db(question=question)
    answer = find_question_answer(question=question)

    return ...


def answer_question():
    return ...


documment = {"question": "Iki kada reikia deklaruoti PVM?", "confirmed": False}
documment_id = insert_document(document=documment)
print(documment_id)
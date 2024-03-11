from app.postgre_entities import (
    ChatBotUser,
    Question,
    Answer,
    Session,
    create_question,
    create_answer,
)


def select_intention(viber_id, message):
    session = Session()
    user = session.query(ChatBotUser).filter(ChatBotUser.viber_id == viber_id).first()
    if message.lower().startswith("klausimas"):
        question = create_question(
            session=session, question_text=message, user_id=user.user_id
        )
        return question

    elif message.lower().startswith("atsakymas"):
        answer = create_answer(
            answer_text=message, question_id=..., user_id=user.user_id
        )
        return answer

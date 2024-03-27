from dataclasses import dataclass


@dataclass
class ViberMessage:
    sender_viber_id: str
    message_text: str
    media_link: str
    tracking_data: dict


@dataclass
class Intention:
    ask_question: bool = False
    list_unanswered_question: bool = False
    answer_question: bool = False
    welcome_help: bool = False


@dataclass
class IntentionName:
    ask_question: str = "klausimas"
    list_unanswered_question: str = "neatsakyti klausimai"
    answer_question: str = "atsakymas"  # don't remember the meaning
    welcome_help: str = "labas"


@dataclass
class TrackingData:
    conversation_id: int = None
    system_message: bool = False
    flow: str = None
    unanswered_question_ids: dict = None


@dataclass
class ConversationStatus:
    active: str = "active"
    pending: str = "pending"
    waiting_for_approval: str = "waiting_for_approval"
    closed: str = "closed"

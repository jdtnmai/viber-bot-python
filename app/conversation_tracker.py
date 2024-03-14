from dataclasses import dataclass, field
from threading import Lock
from typing import List, Dict
import uuid


@dataclass
class Status:
    sender_asked_question = "sender_asked_question"
    responder_writes_answer = "responder_writes_answer"
    responder_submitted_answer = "responder_submitted_answer"
    sender_accepted_answer = "sender_accepted_answer"
    sender_rejected_answer = "sender_rejected_answer"
    conversation_finished = "conversation_finished"


@dataclass
class ConversationStatus:
    conversation_id: str
    sender_id: int
    question_id: int
    status: str
    active_responder_id: int = None
    responders: List[int] = field(default_factory=list)
    last_message_time: float = 0.0


class ConversationManager:
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.conversations = {}

    def get_next_conversation_id(self):
        with self._lock:
            return str(uuid.uuid4())

    def add_conversation(
        self, conversation_id, conversation_status: ConversationStatus
    ):
        with self._lock:
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = conversation_status

    def update_conversation(self, conversation_id: str, updated_attributes: Dict):
        with self._lock:
            for key, value in updated_attributes.items():
                setattr(self.conversations[conversation_id], key, value)

    def remove_conversation(self, conversation_id):
        with self._lock:
            if conversation_id in self.conversations:
                del self.conversations[conversation_id]


conversation_manager = ConversationManager()


def create_conversation(
    conversation_manager, sender_id, question_id, responder_id, responders_list
):
    conversation_id = conversation_manager.get_next_conversation_id()
    conversation = ConversationStatus(
        conversation_id=conversation_id,
        sender_id=sender_id,
        question_id=question_id,
        status=Status.sender_asked_question,
        active_responder_id=responder_id,
    )
    conversation.responders.extend(responders_list)
    conversation_manager.add_conversation(conversation_id, conversation)
    return conversation_id

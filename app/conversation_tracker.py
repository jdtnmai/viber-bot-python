from dataclasses import dataclass, field
from threading import Lock
from typing import List, Dict
import uuid
from logger import logger


@dataclass
class Status:
    sender_started_conversation = "sender_started_conversation"
    sender_asked_question = "sender_asked_question"
    sent_question_to_responder = "sent_question_to_responder"
    responder_writes_answer = "responder_writes_answer"
    responder_submitted_answer = "responder_submitted_answer"
    sender_accepted_answer = "sender_accepted_answer"
    sender_rejected_answer = "sender_rejected_answer"
    conversation_finished = "conversation_finished"


@dataclass
class CSAttributes:
    conversation_id = "conversation_id"
    sender_id = "sender_id"
    question_id = "question_id"
    status = "status"
    active_responder_id = "active_responder_id"
    responders = "responders"
    last_message_time = "last_message_time"


@dataclass
class ConversationStatus:
    conversation_id: str
    sender_id: int
    question_id: int
    status: str = Status.sender_started_conversation
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
        with self._lock:
            if not hasattr(self, "conversations"):
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

    def get_conversation(self, conversation_id) -> ConversationStatus:
        with self._lock:
            if conversation_id in self.conversations:
                return self.conversations[conversation_id]

    def get_conversation_status(self, conversation_id):
        with self._lock:
            logger.debug(
                f"conversation_id value: {conversation_id}. get_conversation_status, {self.conversations}"
            )
            if conversation_id in self.conversations:
                return self.conversations[conversation_id].status

    def is_user_available(self, user_id):
        with self._lock:
            if [
                conversation.sender_id
                for conversation in self.conversations
                if (conversation.sender_id == user_id)
                & (
                    conversation.status
                    not in (Status.conversation_finished, Status.sender_accepted_answer)
                )
            ] or [
                conversation.active_responder_id
                for conversation in self.conversations
                if (conversation.active_responder_id == user_id)
                & (
                    conversation.status
                    not in (
                        Status.conversation_finished,
                        Status.sender_accepted_answer,
                        Status.sender_rejected_answer,
                    )
                )
            ]:
                return False
            else:
                return True


conversation_manager = ConversationManager()


def create_conversation(sender_id, question_id):
    conversation_id = conversation_manager.get_next_conversation_id()
    conversation = ConversationStatus(
        conversation_id=conversation_id,
        sender_id=sender_id,
        question_id=question_id,
    )

    conversation_manager.add_conversation(conversation_id, conversation)
    return conversation_id

from dataclasses import asdict
from app.data_classes import TrackingData, ViberMessage
from app.flows.constants import WELCOME_HELP_MESSAGE
from app.message_utils import MessageBuilder, MessageSenger


def send_welcome_help_message(viber, viber_message: ViberMessage):
    welcome_help_message_text = WELCOME_HELP_MESSAGE
    tracking_data = TrackingData(system_message=True)

    viber_message = MessageBuilder.build_viber_message(
        message_text=welcome_help_message_text,
        tracking_data=asdict(tracking_data),
    )
    MessageSenger.send_viber_messagess(
        viber=viber,
        recipient_viber_id=viber_message.sender_viber_id,
        viber_message=viber_message,
    )

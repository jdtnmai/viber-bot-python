import unittest
from unittest.mock import Mock, patch
from app.flow_manager import FlowManager


class TestFlowManager(unittest.TestCase):
    @patch("app.message_utils.MessageSenger.send_viber_messagess")
    def test_welcome_help_flow(self, mock_send_message):
        # Setup
        session_mock = Mock()
        viber_mock = Mock()
        request_mock = Mock()
        request_mock.message.to_dict.return_value = {
            "text": "labas",
            "sender": {"id": "test_sender_id"},
        }

        fm = FlowManager(
            session=session_mock, viber=viber_mock, viber_request=request_mock
        )

        # Exercise
        fm.welcome_help_flow()

        # Verify
        mock_send_message.assert_called_once()
        args, kwargs = mock_send_message.call_args
        self.assertIn("WELCOME_HELP_MESSAGE", kwargs["viber_message"]["message_text"])
        self.assertEqual(kwargs["recipient_viber_id"], "test_sender_id")


if __name__ == "__main__":
    unittest.main()

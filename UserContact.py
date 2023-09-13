import twilio.rest
import dotenv
import os

dotenv.load_dotenv("tokens.env")


class UserContact:
    """
    Class which houses all the necissary methods for contacting a user outside of Discord
    Once a spot in their courses opens up

    Attributes:
    twilio: twilio.rest.Client object which is used to send SMS messages to a user's phone number
    """

    def __init__(self) -> None:
        account_sid = 'AC2b1a7015a561484c6b94c1550f79c011'
        auth_token = os.getenv("TWILIOAUTH")
        self.twilio = twilio.rest.Client(account_sid, auth_token)

        self.contact_methods = {
            "phone_number": self._process_phone_number,
        }
        self.version = "ContactCore V3.2"

    def contact_user(self, user_profile: dict[str, str], message: str, dlc: dict) -> None:
        """
        Method which handles the profile of a user and contacts them
        """
        for key, value in user_profile.items():
            self.contact_methods.get(key, lambda str1, str2, str3: None)(value, message, dlc)

    def _process_phone_number(self, number: str, message: str, dlc: dict) -> None:
        if not number['confirmed']:
            return
        if dlc['SMS_enabled'] and number['SMS']:
            self._send_sms(number['number'], message)
        
        if dlc['call_enabled'] and number['call']:
            self._make_phonecall(number['number'], message)
        
    def confirm_user_number(self, number: str, confirmation_code: int):
        """
        Sends a confirmation code to a user's phone number
        """
        return
        message = self.twilio.messages.create(
            from_='+18506600835',
            body=f"Your confirmation code is {confirmation_code}. Use /profile confirm with this code to confirm your phone number and activate SMS or phone call notifications. If you didn't request this message, you can safely ignore it.",
            to=number
        )

    def _send_sms(self, number: str, message: str) -> None:
        """
        Uses Twilio to send an SMS message to a user
        """
        message = self.twilio.messages.create(
            from_='+18506600835',
            body=message,
            to=number
        )

    def _make_phonecall(self, number: str, message: str) -> None:
        """
        Uses Twilio to make a phone call to a user
        """
        call = self.twilio.calls.create(
            twiml=f'<Response><Say voice="Polly.Joanna">Hello! This is a message from Ibra Soft T T B Tracker. {message}. Thank you for using T T B Tracker. Have a great day!</Say><Hangup/></Response>',
            to=number,
            from_='+18506600835',
            machine_detection="DetectMessageEnd",
            async_amd=True
            )
    
    
    
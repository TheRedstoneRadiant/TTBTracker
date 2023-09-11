import twilio.rest
import instagrapi
import dotenv
import os

dotenv.load_dotenv("tokens.env")


class UserContact:
    """
    Class which houses all the necissary methods for contacting a user outside of Discord
    Once a spot in their courses opens up

    Attributes:
    instagram: instagrapi.Client object which is used to send messages to a user's instagram account
    twilio: twilio.rest.Client object which is used to send SMS messages to a user's phone number
    """

    def __init__(self) -> None:
        # self.instagram = instagrapi.Client()
        # self.instagram.login(os.getenv("INSTAUSER"), os.getenv("INSTAPASS"))
        account_sid = 'AC2b1a7015a561484c6b94c1550f79c011'
        auth_token = os.getenv("TWILIOAUTH")
        self.twilio = twilio.rest.Client(account_sid, auth_token)

        self.contact_methods = {
            "phone_number": self._process_phone_number,
            "instagram": self._send_insta_message
        }

    def contact_user(self, user_profile: dict[str, str], message: str) -> None:
        """
        Method which handles the profile of a user and contacts them
        """
        for key, value in user_profile.items():
            self.contact_methods[key](value, message)

    def _process_phone_number(self, number: str, message: str) -> None:
        if not number['confirmed']:
            return
        if number['SMS']:
            self._send_sms(number['number'], message)
        
        if number['call_notifications_activated'] and number['call']:
            self._make_phonecall(number['number'], message)
        
    def confirm_user_number(self, number: str, confirmation_code: int):
        """
        Sends a confirmation code to a user's phone number
        """
        message = self.twilio.messages.create(
            from_='+18506600835',
            body=f"Your confirmation code is {confirmation_code}. Use /profile confirm with this code to confirm your phone number and activate SMS or phone call notifications. If you didn't request this message, you can safely ignore it.",
            to=number
        )

    def _send_insta_message(self, username: str, message: str) -> None:
        """
        Sends a message to a user's instagram account
        """
        if username['enabled']:
            return
            send_to = self.instagram.user_id_from_username(username=username['username'])
            self.instagram.direct_send(text=message, user_ids=[send_to])
        

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
    
    
    
from twilio.rest import Client
import os

class SMSClient:
    def __init__(self):
        """
        Initializes the SMSClient with Twilio credentials.
        """
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")  # Twilio Account SID
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")    # Twilio Auth Token
        self.twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")  # Twilio Phone Number
        self.client = Client(self.account_sid, self.auth_token)

    def send_sms(self, phone_code, phone_number, message):
        """
        Sends an SMS message using the Twilio API.

        :param phone_code: Country code (e.g., "66" for Thailand)
        :param phone_number: The recipient's phone number
        :param message: The SMS message content
        :return: The Twilio API response
        """
        try:
            # Combine the phone code and phone number
            full_phone_number = f"+{phone_code}{phone_number}"

            # Send the SMS via Twilio
            message_response = self.client.messages.create(
                to=full_phone_number,
                from_=self.twilio_phone_number,
                body=message
            )

            # Return the Twilio response details
            return {
                "sid": message_response.sid,
                "status": message_response.status,
                "date_created": message_response.date_created,
                "to": message_response.to,
                "from": message_response.from_,
            }
        except Exception as e:
            print(f"Error sending SMS: {e}")
            return None
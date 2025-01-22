import requests
import os 

class SMSClient:
    def __init__(self):
        """
        Initializes the SMSClient with the base URL, access key ID, and token.
        
        :param access_key_id: Your access key ID for authentication
        :param access_key_token: Your access key token for authentication
        """
        self.headers = {
            'accept': '*/*',
            "Access-Key-ID": os.getenv("TDC_SMS_ACCESS_ID"),
            "Access-Key-Token": os.getenv("TDC_SMS_ACCESS_TOKEN"),
            'Content-Type': 'application/json'
        }

    def send_sms(self, phone_code, phone_number, message):
        """
        Sends an SMS message using the API.

        :param phone_code: Country code (e.g., "66" for Thailand)
        :param phone_number: The recipient's phone number
        :param sender_id: The sender's ID (e.g., "TDC")
        :param message: The SMS message content
        :return: The API response
        """

        body = {
            "phoneCode": phone_code,
            "phoneNumber": phone_number,
            "senderId": "MNDC2025",
            "message": message,
        }
        try:
            response = requests.post("https://mooping-openapi.thaidata.cloud/v1.1/sms-simple", headers=self.headers, json=body)
            response.raise_for_status()  # Raise an error for HTTP status codes >= 400
            return response.json()  # Return the JSON response if successful
        except requests.exceptions.RequestException as e:
            print(f"Error sending SMS: {e}")
            print(e.response.text)
            return None
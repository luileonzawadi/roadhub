import os
from twilio.rest import Client

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'AC_fake_sid')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'fake_auth_token')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

def send_whatsapp_greeting(phone_number, name, interest):
    """
    Sends an automated WhatsApp greeting via Twilio Sandbox.
    """
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Ensure number has whatsapp: prefix and + sign
        if not phone_number.startswith('whatsapp:'):
            if not phone_number.startswith('+'):
                # Assuming Kenya as default for Roadshub if no +
                if phone_number.startswith('0'):
                    phone_number = '+254' + phone_number[1:]
                else:
                    phone_number = '+' + phone_number
            to_number = f"whatsapp:{phone_number}"
        else:
            to_number = phone_number
            
        message_body = (
            f"Habari {name}! Welcome to Roadshub. 🏗️\n\n"
            f"We noticed you're interested in {interest}. "
            "Our flagship courses are designed to get you Autodesk ACP Certified in Civil 3D and AutoCAD.\n\n"
            "Check out our recommended cohort here: https://roadshub.org/courses\n\n"
            "Reply to this message if you have any questions!"
        )
        
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message_body,
            to=to_number
        )
        return {"status": "success", "sid": message.sid}
    except Exception as e:
        return {"error": str(e)}

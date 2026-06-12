import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', 'fake_sg_key')
FROM_EMAIL = os.environ.get('MAIL_DEFAULT_SENDER', 'hello@roadshub.com')

def send_nurture_sequence_email(to_email, name, day):
    """
    Dispatches sequence emails. day=1 (Welcome), day=3 (Case Study), day=7 (Cohort Reminder)
    """
    if day == 1:
        subject = f"Welcome to Roadshub, {name}!"
        content = "Here is your free ACP Study Guide PDF link..."
    elif day == 3:
        subject = f"See how {name} passed their ACP Exam"
        content = "Case study of a past student who mastered Corridor Modeling..."
    elif day == 7:
        subject = "Next Cohort Enrolling Soon 🚀"
        content = "Don't miss out on our upcoming Civil 3D cohort..."
    else:
        return {"error": "Invalid day sequence"}
        
    try:
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=f"<strong>{content}</strong>"
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return {"status": "success", "status_code": response.status_code}
    except Exception as e:
        return {"error": str(e)}

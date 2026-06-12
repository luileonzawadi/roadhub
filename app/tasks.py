from celery_worker import celery
from app.models import db, Lead
from app.utils.whatsapp import send_whatsapp_greeting
from app.utils.email import send_nurture_sequence_email

@celery.task(name='tasks.send_whatsapp_message_task')
def send_whatsapp_message_task(lead_id):
    lead = Lead.query.get(lead_id)
    if lead and lead.phone_number:
        send_whatsapp_greeting(lead.phone_number, lead.name, lead.area_of_interest)

@celery.task(name='tasks.send_nurture_email_task')
def send_nurture_email_task(lead_id, day):
    lead = Lead.query.get(lead_id)
    if lead and lead.email:
        send_nurture_sequence_email(lead.email, lead.name, day)

@celery.task(name='tasks.evaluate_lead_intent_task')
def evaluate_lead_intent_task(lead_id):
    lead = Lead.query.get(lead_id)
    if lead:
        if lead.email_opened and lead.pricing_page_visited:
            lead.is_high_intent = True
            db.session.commit()

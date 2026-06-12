import os
import stripe

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_fake_key_for_sandbox')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', 'whsec_fake_key')

def create_checkout_session(course, payment_id, success_url, cancel_url):
    """
    Creates a Stripe Checkout session.
    Expects course.price to be in USD float.
    """
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': course.title,
                        'images': [course.cover_image_url] if course.cover_image_url else [],
                    },
                    'unit_amount': int(course.price * 100),  # Amount in cents
                },
                'quantity': 1,
            }],
            mode='payment',
            client_reference_id=str(payment_id),
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session
    except Exception as e:
        return {"error": str(e)}

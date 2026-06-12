import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import base64

# Safaricom Sandbox settings (can be overridden by env vars)
MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', 'sandbox_consumer_key')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', 'sandbox_consumer_secret')
MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')
MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE', '174379')
MPESA_ENV = os.environ.get('MPESA_ENV', 'sandbox')  # 'sandbox' or 'production'

def get_mpesa_access_token():
    if MPESA_ENV == 'sandbox':
        url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    else:
        url = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        
    try:
        response = requests.get(url, auth=HTTPBasicAuth(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET), timeout=10)
        if response.status_code == 200:
            return response.json().get('access_token')
        return None
    except Exception as e:
        print(f"Error fetching access token: {e}")
        return None

def initiate_stk_push(phone_number, amount, account_reference, transaction_desc, callback_url):
    """
    Triggers an STK push to the given phone number.
    amount should be an integer for KES.
    """
    token = get_mpesa_access_token()
    if not token:
        return {"error": "Failed to get access token"}
        
    if MPESA_ENV == 'sandbox':
        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    else:
        api_url = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password_str = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(password_str.encode('utf-8')).decode('utf-8')
    
    # Format phone number to start with 254 (e.g. 0712345678 -> 254712345678)
    if phone_number.startswith('0'):
        phone_number = "254" + phone_number[1:]
    elif phone_number.startswith('+'):
        phone_number = phone_number[1:]
        
    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone_number,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_desc
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=15)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

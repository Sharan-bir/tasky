from django.core.mail import send_mail
from django.conf import settings
import random
import string

def send_otp_email(email: str) -> str:
    otp = ''.join(random.choices(string.digits, k=6))
    subject = 'Your OTP for Tasky'
    message = f'Your OTP is: {otp}'
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )
    return otp
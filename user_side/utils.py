from django.core.mail import send_mail
from django.conf import settings
import random
from .models import OTPVerification

def send_otp_email(email):
    otp = ''.join(random.choices('0123456789', k=6))
    otp_instance = OTPVerification.objects.create(user=email, otp=otp)
    otp_instance.save()

    # Send email with OTP
    send_mail(
        'Your OTP Code',
        f'Your OTP code is: {otp}',
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False,
    )
    return otp_instance
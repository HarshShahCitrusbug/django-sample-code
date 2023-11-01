"""This file includes the function for the sendgrid mail functionality"""

from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from python_http_client import exceptions

from utils.django.exceptions import SendgridEmailException


def sendgrid_mail(to_email: str, TEMPLATE_KEY: str, dynamic_data_for_template: dict):
    """
    This function is used to send emails using Sendgrid
    """
    SENDGRID_API_KEY = getattr(settings, "SENDGRID_API_KEY", None)
    SENDGRID_FROM_MAIL = getattr(settings, "SENDGRID_FROM_MAIL", None)
    message = Mail(
        from_email=SENDGRID_FROM_MAIL,
        to_emails=to_email,
    )
    message.dynamic_template_data = dynamic_data_for_template
    message.template_id = TEMPLATE_KEY
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return response
    except exceptions.BadRequestsError as e:
        print("Exception in sending mail :", e)
        raise SendgridEmailException(message="Something went wrong in sending mails.", item={'error': e})

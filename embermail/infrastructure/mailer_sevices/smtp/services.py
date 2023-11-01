import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl

from django.conf import settings
from django.template.loader import render_to_string


class SMTPServices:

    def __init__(self, email_provider: str, username: str, app_password: str):
        self.host = 'smtp.gmail.com' if email_provider == 'gmail' else 'smtp.office365.com'
        self.username = username
        self.password = app_password

    def set_smtp_server_configurations(self) -> smtplib.SMTP:
        """
        Get Connection to SMTP server
        """
        try:
            # SMTP server configurations
            smtp_host = self.host
            smtp_port = 587
            smtp_username = self.username
            smtp_password = self.password

            # Create a secure SSL context
            context = ssl.create_default_context()

            # Connect to the SMTP server
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls(context=context)
            server.login(smtp_username, smtp_password)
            return server
        except Exception as e:
            raise e

    def configure_email_data(self, subject: str, body: str, to: str, message_id: str = None) -> EmailMessage:
        """
        Setup Email Parameters to Message Object
        """
        # EMAIL SETUP
        subject = subject
        body = body

        # Create Email Message using MIMEMultipart
        message_object = MIMEMultipart('alternative')
        message_object['From'] = f'{self.username.split("@")[0]} <{self.username}>'
        message_object['To'] = to
        message_object['Subject'] = subject
        message_object['Reply-to'] = self.username
        if message_id:
            message_object['In-Reply-To'] = message_id
            message_object['References'] = message_id

        part = MIMEText(body, 'html')
        message_object.attach(part)
        return message_object

    def send_mail(self, to: str, subject: str, body: str, message_id: str = None) -> list:
        """
        Send Mail using SMTP
        """
        try:
            server = self.set_smtp_server_configurations()
            message_object = self.configure_email_data(subject=subject, body=body, to=to, message_id=message_id)
            mail_status = server.sendmail(self.username, to, message_object.as_string())

            server.quit()
            return mail_status
        except Exception as e:
            print(e)
            pass

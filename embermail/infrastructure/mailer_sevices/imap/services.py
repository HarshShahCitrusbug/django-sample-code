import imaplib
import email


class IMAPServices:
    def __init__(self, email_provider: str, username: str, app_password: str):
        self.host = 'imap.gmail.com' if email_provider == 'gmail' else 'outlook.office365.com'
        self.username = username
        self.password = app_password

    def get_connection_with_imap(self):
        try:
            imap = imaplib.IMAP4_SSL(self.host)
            imap.login(self.username, self.password)

            return imap
        except Exception as e:
            print('Connection Aborted...', e)

    def get_latest_mail_message_id_by_subject(self, subject: str, receiver_email: str):
        try:
            imap = self.get_connection_with_imap()
            imap.select('Inbox')
            # Get Mails which one's Subject is Matching
            search_query = f'(FROM "{receiver_email}" SUBJECT "{subject}")'
            result, email_ids = imap.search(None, search_query)
            message_id = None
            if result == "OK" and email_ids[0]:
                email_ids = email_ids[0].split()
                result, email_data = imap.fetch(email_ids[-1], "(RFC822)")
                if result:
                    raw_email = email_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    message_id = msg.get("Message-ID").strip()
            return message_id
        except Exception as e:
            print(e)
            pass

    def read_mail_by_subject(self, subject: str):
        try:
            imap = self.get_connection_with_imap()
            imap.select('Inbox')
            # Get Mails which one's Subject is Matching
            search_query = f'(SUBJECT "{subject}")'
            result, email_ids = imap.search(None, search_query)
            email_ids = email_ids[0].split()
            if result == "OK" and email_ids:
                for ids in email_ids:
                    result, email_data = imap.fetch(ids, "(RFC822)")
            return True
        except Exception as e:
            print(e)
            pass

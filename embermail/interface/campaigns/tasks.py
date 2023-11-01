import email
import time
import random
import logging
import datetime

from celery import shared_task
from django.conf import settings
from django.db.models import OuterRef, Subquery

from utils.data_manipulation.encryption import SecretEncryption
from embermail.application.users.services import UserAppServices
from embermail.domain.campaigns.models import CampaignReportData
from embermail.infrastructure.logger.models import AttributeLogger
from embermail.domain.text_choices import CampaignActionRequiredChoices
from embermail.application.campaigns.services import CampaignAppServices
from embermail.infrastructure.mailer_sevices.services import sendgrid_mail
from embermail.infrastructure.mailer_sevices.imap.services import IMAPServices
from embermail.infrastructure.mailer_sevices.smtp.services import SMTPServices
from embermail.domain.templates.services import ThreadServices, TemplateServices

record_log = AttributeLogger(logging.getLogger("record_logger"))


@shared_task
def main_algorithm():
    try:
        # Initialize Thread and Template Repo
        thread_repo = ThreadServices().get_thread_repo()
        template_repo = TemplateServices().get_template_repo()

        # Start Time Counter
        time_counter.delay()

        # Get All Campaign Which is Going to be Warmup
        all_campaigns = CampaignAppServices().list_campaigns().filter(is_stopped=False, app_password__isnull=False,
                                                                      action_required=CampaignActionRequiredChoices.NONE)
        for campaign in all_campaigns:
            # Get Encrypted App Password and Checking App Password, Plan ID, Email Service Provider are available
            app_password = SecretEncryption().decrypt_secret_string(encrypted_string=campaign.app_password)
            if campaign.plan_id and app_password and campaign.email_service_provider in ['gmail', 'outlook']:
                # Get Total mails to be sent and update it by step up
                total_mails_to_send = campaign.mails_to_be_sent
                if int(campaign.mails_to_be_sent) < int(campaign.max_email_per_day):
                    total_mails_to_send = int(campaign.mails_to_be_sent) + int(
                        campaign.email_step_up)
                    campaign.mails_to_be_sent = total_mails_to_send
                    campaign.save()

                domain_list = CampaignAppServices().list_domain_lists().filter(is_active=True)
                receivers_data_dict_list = [email for email in
                                            domain_list.values('email', 'app_password', 'email_service_provider')]

                thread_subquery = thread_repo.filter(template_id=OuterRef("id")).order_by("-thread_ordering_number")

                templates_list = list(template_repo.filter(warmup_email=campaign.email).annotate(
                    total_threads=Subquery(thread_subquery.values("thread_ordering_number")[:1])))
                if not templates_list:
                    templates_list = list(template_repo.filter(is_general=True).annotate(
                        total_threads=Subquery(thread_subquery.values("thread_ordering_number")[:1])))
                random_templates = random.sample(templates_list, len(templates_list))

                total_threads = 0
                max_threads_in_template = 0
                finalized_templates = []

                template_number = 0
                while True:
                    if total_threads < (2 * total_mails_to_send) and total_threads - (2 * total_mails_to_send) <= -2:
                        finalized_templates.append(random_templates[template_number])
                        template_number += 1
                        if template_number == len(random_templates):
                            template_number = 0
                        if random_templates[template_number].total_threads > max_threads_in_template:
                            max_threads_in_template = random_templates[template_number].total_threads
                        total_threads += random_templates[template_number].total_threads
                    else:
                        break

                if len(receivers_data_dict_list) < len(finalized_templates):
                    finalized_templates = finalized_templates[:len(receivers_data_dict_list)]
                finalized_receivers_dict = random.sample(receivers_data_dict_list, len(finalized_templates))

                template_fixture = list()
                for index in range(len(finalized_templates)):
                    data_dict = dict()
                    # Receivers
                    data_dict["receiver_email"] = finalized_receivers_dict[index].get('email')
                    data_dict["app_password"] = finalized_receivers_dict[index].get('app_password')
                    data_dict["email_provider"] = finalized_receivers_dict[index].get('email_service_provider')
                    data_dict["template_name"] = finalized_templates[index].name
                    data_dict["template_subject"] = finalized_templates[index].subject

                    threads = (
                        thread_repo.filter(template_id=finalized_templates[index].id)
                        .order_by("thread_ordering_number")
                        .values_list("body", flat=True)
                    )
                    data_dict["thread_list"] = list(threads)
                    data_dict["thread_count"] = len(data_dict["thread_list"])
                    template_fixture.append(data_dict)

                # Email Data
                sender_data_dict = dict()
                sender_data_dict['email'] = campaign.email
                sender_data_dict['email_service_provider'] = campaign.email_service_provider
                sender_data_dict['app_password'] = app_password

                for template in template_fixture:
                    max_time_to_complete_all_process = int(getattr(settings, "MAX_TIME_TO_COMPLETE_ALGORITHM", "72000"))
                    time_to_be_sent_one_mail = int(max_time_to_complete_all_process / max_threads_in_template * 0.98)
                    delay_for_sending_mail = random.randint(1, time_to_be_sent_one_mail)
                    message_id = 0
                    send_email_task_schedular.apply_async(
                        (delay_for_sending_mail, "sender", sender_data_dict, template.get('thread_list'), 0,
                         template.get('template_subject'), time_to_be_sent_one_mail, template.get('receiver_email'),
                         template.get('app_password'), template.get('email_provider'), message_id, total_mails_to_send),
                        countdown=delay_for_sending_mail,
                    )
    except Exception as e:
        print("error in main_algorithm:", e.__traceback__.tb_lineno, e.__traceback__)
    return "All Campaign Algorithm Completed Successfully."


@shared_task
def time_counter():
    start_time = time.time()
    while True:
        timer = time.time() - start_time
        print(f"============>> Timer Counter : {timer} <<=============")
        time.sleep(1)
        if int(timer) > 1000:
            break


@shared_task
def send_email_async(email_provider, username, app_password, to, subject, body, message_id=None) -> str:
    if getattr(settings, "ENABLE_SEND_MAILS_FOR_WARMUP", None):
        SMTPServices(email_provider=email_provider, username=username,
                     app_password=app_password).send_mail(to=to,
                                                          subject=subject,
                                                          body=body,
                                                          message_id=message_id)
        return "Mail Sent"
    return "Enable 'ENABLE_SEND_MAILS_FOR_WARMUP' in settings.py"


@shared_task
def read_mails_async(email_provider: str, username: str, app_password: str, subject: str) -> str:
    if getattr(settings, "ENABLE_SEND_MAILS_FOR_WARMUP", None):
        IMAPServices(email_provider=email_provider, username=username, app_password=app_password).read_mail_by_subject(
            subject=subject)
        return "Mail Read"


@shared_task
def send_mail_and_creates_attribute_logs(email_provider: str, username: str, app_password: str, subject: str,
                                         updated_body: str, to: str, sender_data: dict, receiver_data: dict,
                                         thread_to_send: int, log_message: str, message_id_for_mail: str) -> str:
    parent_mail_message_id = None
    mail_sent_successfully = False
    if getattr(settings, "ENABLE_SEND_MAILS_FOR_WARMUP", None):
        if thread_to_send == 0:
            send_email_async.delay(email_provider=email_provider, username=username, app_password=app_password, to=to,
                                   subject=subject, body=updated_body)
            mail_sent_successfully = True
        else:
            parent_mail_message_id = IMAPServices(email_provider=email_provider, username=username,
                                                  app_password=app_password).get_latest_mail_message_id_by_subject(
                subject=subject, receiver_email=receiver_data.get('email'))
            if parent_mail_message_id:
                subject = f"Re: {subject}"
                send_email_async.delay(email_provider=email_provider, username=username, app_password=app_password,
                                       to=to, subject=subject, body=updated_body, message_id=parent_mail_message_id)
                mail_sent_successfully = True
    attributes_log = record_log.with_attributes(sender=sender_data, receiver=receiver_data,
                                                mail_sent_status=mail_sent_successfully,
                                                template_subject=subject,
                                                message_id=parent_mail_message_id,
                                                thread_number=int(thread_to_send) + 1, body=updated_body)
    attributes_log.fatal(log_message)


@shared_task
def send_email_task_schedular(delay, mail_sender, sender_data_dict, thread_list, thread_to_send, template_subject,
                              time_to_be_sent_one_mail, receiver_email, receiver_app_password, receiver_email_provider,
                              message_id, total_mails_to_send):
    if mail_sender == "sender" and thread_to_send < len(thread_list):
        try:
            sender_name = CampaignAppServices().get_user_first_name_by_warmup_email(
                warmup_email=sender_data_dict.get('email'))
        except Exception:
            sender_name = sender_data_dict.get('email').split("@")[0]
        receiver_name = receiver_email.split("@")[0]
        body = thread_list[int(thread_to_send)]
        updated_body = body.replace("{{test_user1}}", f"<b>{sender_name}</b>").replace("{{test_user2}}",
                                                                                       f"<b>{receiver_name}</b>")
        email_provider = sender_data_dict.get('email_service_provider')
        username = sender_data_dict.get('email')
        app_password = sender_data_dict.get('app_password')

        # Calculating Total Number of Sent Mails
        read_file_date = datetime.datetime.now().strftime("%Y-%m-%d")
        total_number_of_sent_mail = CampaignAppServices().calculate_total_sent_mails_by_sender_email(
            file_date=read_file_date, sender_email=username)

        if total_number_of_sent_mail < total_mails_to_send:
            sender_data = {
                "name": sender_name,
                "email": username,
                "email_provider": email_provider,
                "send_max_emails_per_day": total_mails_to_send,
                "total_number_of_sent_mails": total_number_of_sent_mail + 1
            }
            receiver_data = {
                "name": receiver_name,
                "email": receiver_email,
                "email_provider": receiver_email_provider
            }
            log_message = "Mail Sent Successfully from Warmup Email to User."
            send_mail_and_creates_attribute_logs.delay(email_provider=email_provider, username=username,
                                                       app_password=app_password, subject=template_subject,
                                                       updated_body=updated_body,
                                                       to=receiver_email, sender_data=sender_data,
                                                       receiver_data=receiver_data,
                                                       thread_to_send=thread_to_send, log_message=log_message,
                                                       message_id_for_mail=message_id)

            print("*********************************************************************")
            print(f"sender email: {sender_data_dict.get('email')}")
            print(f"to: {receiver_email}")
            print(f"Template Subject:{template_subject}")
            print(f"sent mail body index: {thread_to_send}")
            print(f"delay:{delay}")
            print(f"Total Mails to Send:{total_mails_to_send}")
            print(f"Sent Mails Number:{total_number_of_sent_mail + 1}")
            print("*********************************************************************")
            thread_to_send = int(thread_to_send) + 1
            send_email_task_schedular.apply_async(
                (random.randint(int(time_to_be_sent_one_mail * 3 / 4), time_to_be_sent_one_mail), "receiver",
                 sender_data_dict, thread_list, thread_to_send, template_subject, time_to_be_sent_one_mail,
                 receiver_email, receiver_app_password, receiver_email_provider, message_id, total_mails_to_send),
                countdown=delay, )
    elif thread_to_send < len(thread_list):
        sender_name = receiver_email.split("@")[0]
        try:
            receiver_name = CampaignAppServices().get_user_first_name_by_warmup_email(
                warmup_email=sender_data_dict.get('email'))
        except Exception:
            receiver_name = sender_data_dict.get('email').split("@")[0]
        body = thread_list[int(thread_to_send)]
        updated_body = body.replace("{{test_user2}}", f"<b>{sender_name}</b>").replace("{{test_user1}}",
                                                                                       f"<b>{receiver_name}</b>")
        app_password = SecretEncryption().decrypt_secret_string(encrypted_string=receiver_app_password)
        # if not message_id and (receiver_email_provider == 'outlook' or sender_data_dict.get(
        #         'email_service_provider') == 'outlook'):
        #     message_id = IMAPServices(email_provider=receiver_email_provider, app_password=app_password,
        #                               username=receiver_email).get_latest_mail_message_id_by_subject(
        #         subject=template_subject, receiver_email=receiver_email)

        sender_data = {
            "name": sender_name,
            "email": receiver_email,
            "email_provider": receiver_email_provider
        }
        receiver_data = {
            "name": receiver_name,
            "email": sender_data_dict.get('email'),
            "email_provider": sender_data_dict.get('email_service_provider')
        }
        log_message = "Mail Sent Successfully from User to Warmup Email."
        send_mail_and_creates_attribute_logs.delay(email_provider=receiver_email_provider, username=receiver_email,
                                                   app_password=app_password, subject=template_subject,
                                                   updated_body=updated_body,
                                                   to=sender_data_dict.get('email'), sender_data=sender_data,
                                                   receiver_data=receiver_data, thread_to_send=thread_to_send,
                                                   log_message=log_message, message_id_for_mail=message_id)
        print("*********************************************************************")
        print(f"sender email: {receiver_email}")
        print(f"to: {sender_data_dict.get('email')}")
        print(f"Template Subject:{template_subject}")
        print(f"sent mail body index: {thread_to_send}")
        print(f"delay:{delay}")
        print("*********************************************************************")
        thread_to_send = int(thread_to_send) + 1
        send_email_task_schedular.apply_async(
            (
                random.randint(int(time_to_be_sent_one_mail * 3 / 4), time_to_be_sent_one_mail),
                "sender",
                sender_data_dict,
                thread_list,
                thread_to_send,
                template_subject,
                time_to_be_sent_one_mail,
                receiver_email,
                receiver_app_password,
                receiver_email_provider,
                message_id,
                total_mails_to_send
            ),
            countdown=delay,
        )
    return "A Campaign Algorithm Completed."


@shared_task
def create_campaign_reports_by_log_records() -> str:
    """
    Creates Campaign Reports
    """
    # report_date = (datetime.datetime.now() - datetime.timedelta(days=1)).date()
    report_date = (datetime.datetime.now()).date()
    file_date = report_date.strftime("%Y-%m-%d")
    raw_df = CampaignAppServices().read_record_file_to_list_of_dict(file_date=file_date)
    # TODO : Remove Below 1 line
    # raw_df.to_excel(f"utils/embermail_data_excels/raw_df.xlsx", index=False)
    domain_emails_list = CampaignAppServices().list_domain_lists_by_is_active()

    for domain_email in domain_emails_list:
        receiver_email = domain_email.email
        email_service_provider = domain_email.email_service_provider
        app_password = CampaignAppServices().decrypt_app_password(
            encrypted_app_password=domain_email.app_password)
        imap = IMAPServices(email_provider=email_service_provider, username=receiver_email,
                            app_password=app_password).get_connection_with_imap()

        for campaign in CampaignAppServices().list_campaigns().filter(is_active=True, is_stopped=False):
            filtered_df = raw_df[
                (raw_df['receiver_email'] == receiver_email) & (raw_df['sender_email'] == campaign.email)]
            if not filtered_df.empty:
                total_sent_mails = len(filtered_df)
                start_date = report_date.strftime('%d-%b-%Y')
                end_date = (report_date + datetime.timedelta(days=1)).strftime('%d-%b-%Y')
                inbox_count = 0
                category_count = 0
                spam_count = 0
                if email_service_provider == 'gmail':
                    imap.select('"[Gmail]/All Mail"')
                    search_criteria = f'(SINCE {start_date} BEFORE {end_date} FROM {campaign.email})'
                    result, email_ids = imap.search(None, search_criteria)
                    if result:
                        filtered_email_ids = str(email.message_from_bytes(email_ids[0])).strip().split(
                            " ") if b"" not in email_ids else list()
                        if filtered_email_ids:
                            for email_id in filtered_email_ids:
                                tmp, data = imap.fetch(f'{email_id}', '(X-GM-LABELS)')
                                label_list = data[0].decode('utf-8').split('X-GM-LABELS (')[1].split(")")[
                                    0].replace("\\", "").replace('"', '').strip().split(" ")
                                if 'Inbox' in label_list:
                                    inbox_count += 1
                                else:
                                    category_count += 1
                    imap.select('[Gmail]/Spam')
                    search_criteria = f'(SINCE {start_date} BEFORE {end_date} FROM {campaign.email})'
                    result, email_ids = imap.search(None, search_criteria)
                    if result == "OK":
                        filtered_email_ids = str(email.message_from_bytes(email_ids[0])).strip().split(
                            " ") if b"" not in email_ids else list()
                        if filtered_email_ids:
                            spam_count += len(filtered_email_ids)

                if email_service_provider == 'outlook':
                    imap.select('Inbox')
                    search_criteria = f'(SINCE {start_date} BEFORE {end_date} FROM {campaign.email})'
                    result, email_ids = imap.search(None, search_criteria)
                    if result == 'OK':
                        filtered_email_ids = str(email.message_from_bytes(email_ids[0])).strip().split(
                            " ") if b"" not in email_ids else list()
                        if filtered_email_ids:
                            inbox_count += len(filtered_email_ids)
                    imap.select('Junk')
                    search_criteria = f'(SINCE {start_date} BEFORE {end_date} FROM {campaign.email})'
                    result, email_ids = imap.search(None, search_criteria)
                    if result == "OK":
                        filtered_email_ids = str(email.message_from_bytes(email_ids[0])).strip().split(
                            " ") if b"" not in email_ids else list()
                        if filtered_email_ids:
                            spam_count += len(filtered_email_ids)
                    category_count += total_sent_mails - inbox_count - spam_count

                # Creating or Updating Campaign Reports
                campaign_report_data = CampaignReportData(email=campaign.email, report_date=report_date,
                                                          inbox_count=inbox_count,
                                                          total_emails_sent=total_sent_mails,
                                                          category_count=category_count, spam_count=spam_count,
                                                          campaign_id=campaign.id, user_id=campaign.user_id,
                                                          master_user_id=campaign.master_user_id)
                campaign_report_instance, created = CampaignAppServices().campaign_report_services.get_campaign_report_factory().get_entity_with_get_or_create(
                    campaign_report_data=campaign_report_data)
                if not created:
                    campaign_report_instance.total_emails_sent += total_sent_mails
                    campaign_report_instance.inbox_count += inbox_count
                    campaign_report_instance.category_count += category_count
                    campaign_report_instance.spam_count += spam_count
                    campaign_report_instance.save()

    # Run Function for Calculating Inbox and Reputation Ratio and Send Emails for Reputation
    calculate_inbox_and_reputation_ratio_with_email_alerts.delay(report_date_string=file_date)

    return f"Campaign Reports Created for {file_date}."


@shared_task
def calculate_inbox_and_reputation_ratio_with_email_alerts(report_date_string: str) -> str:
    """
    Calculates and Updates Inbox Ratio and Reputation Ratio and Send Email if Reputation goes Down to Threshold Limit
    """
    report_date = datetime.datetime.strptime(report_date_string, "%Y-%m-%d")
    campaign_reports = CampaignAppServices().list_campaign_reports().filter(report_date=report_date)
    for campaign_report_instance in campaign_reports:
        total_sent_mails = int(campaign_report_instance.total_emails_sent)
        inbox_count = int(campaign_report_instance.inbox_count)
        category_count = int(campaign_report_instance.category_count)
        campaign_report_instance.inbox_ratio = float(inbox_count / total_sent_mails * 100)
        reputation_ratio = campaign_report_instance.reputation_ratio = float(
            (inbox_count + category_count) / total_sent_mails * 100)
        # TODO : Remove below 2 lines
        if campaign_report_instance.email == 'vipul.citrusbug@gmail.com':
            reputation_ratio = 19.0
        campaign_report_instance.save()
        # Sending Mail for Reputation Alert if < 30
        if reputation_ratio < 30:
            sendgrid_reputation_alert_template_id = getattr(settings, "SENDGRID_REPUTATION_ALERT_TEMPLATE_KEY",
                                                            None)
            base_url = getattr(settings, "BASE_URL", None)
            # Sending Mail to User
            user = UserAppServices().get_user_by_id(id=campaign_report_instance.user_id)
            username = user.first_name if user.first_name else user.email.split('@')[0]
            template_data = {
                'username': username,
                'date_time': report_date_string,
                'email': campaign_report_instance.email,
                'login_link': f"{base_url}/onboarding/"
            }
            sendgrid_mail(to_email=campaign_report_instance.email,
                          TEMPLATE_KEY=sendgrid_reputation_alert_template_id,
                          dynamic_data_for_template=template_data)
            # Sending Mail to Master User
            if not user.is_master_user:
                users_master_id = user.users_master_id
                user = UserAppServices().get_user_by_id(id=users_master_id)
                username = user.first_name if user.first_name else user.email.split('@')[0]
                template_data = {
                    'username': username,
                    'date_time': report_date_string,
                    'email': campaign_report_instance.email,
                    'login_link': f"{base_url}/onboarding/"
                }
                sendgrid_mail(to_email=user.email,
                              TEMPLATE_KEY=sendgrid_reputation_alert_template_id,
                              dynamic_data_for_template=template_data)

    return "Inbox ratio and Reputation ratio Updated with Reputation Alert."

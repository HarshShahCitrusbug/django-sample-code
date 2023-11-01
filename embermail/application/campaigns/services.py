import json
import uuid
import email
import datetime
from uuid import UUID
from typing import Union

import pandas
import pandas as pd
from django.conf import settings
from django.db.models.query import QuerySet

from utils.django.regex import validate_email_by_regex
from utils.data_manipulation.encryption import SecretEncryption
from embermail.application.users.services import UserAppServices
from utils.data_manipulation.type_conversion import encode_by_base64
from embermail.infrastructure.mailer_sevices.services import sendgrid_mail
from embermail.domain.text_choices import CampaignActionRequiredChoices
from embermail.infrastructure.mailer_sevices.smtp.services import SMTPServices
from embermail.infrastructure.mailer_sevices.imap.services import IMAPServices
from embermail.domain.campaigns.models import Campaign, CampaignData, CampaignType, CampaignReport, CampaignReportData, \
    DomainList, DomainListData
from embermail.domain.campaigns.services import CampaignServices, CampaignTypeServices, CampaignReportServices, \
    DomainListServices
from utils.django.exceptions import CampaignDataValidation, CampaignDoesNotExist, InvalidCredentialsException, \
    ValidationException, \
    CampaignAlreadyExist, CampaignCreationException, CampaignTypeDoesNotExist, \
    ActionRequiredException, CampaignReportDoesNotExist, DomainListDoesNotExist, DomainEmailCreationException


class CampaignAppServices:
    campaign_services = CampaignServices()
    campaign_type_services = CampaignTypeServices()
    campaign_report_services = CampaignReportServices()
    domain_list_services = DomainListServices()

    # =====================================================================================
    # CAMPAIGN
    # =====================================================================================
    def get_campaign_by_id(self, id: UUID) -> Campaign:
        """
        Get campaign instance by id
        """
        try:
            return self.campaign_services.get_campaign_repo().get(id=id)
        except Exception as e:
            raise CampaignDoesNotExist(message="Campaign with this id is not registered yet.",
                                       item={'error': e.args})

    def get_campaign_by_email(self, email: str) -> Campaign:
        """
        Get campaign instance by email
        """
        try:
            return self.campaign_services.get_campaign_repo().get(email=email)
        except Exception as e:
            raise CampaignDoesNotExist(message="Campaign with this email is not registered yet.",
                                       item={'error': e.args})

    def list_campaigns(self) -> QuerySet[Campaign]:
        """
        List all campaigns
        """
        return self.campaign_services.get_campaign_repo().all()

    def list_campaigns_by_user_id(self, user_id: UUID) -> QuerySet[Campaign]:
        """
        List all campaigns by user_id
        """
        return self.list_campaigns().filter(user_id=user_id)

    def list_campaigns_by_master_user_id(self, master_user_id: UUID) -> QuerySet[Campaign]:
        """
        List all campaigns have master user by master_user_id
        """
        return self.list_campaigns().filter(master_user_id=master_user_id)

    def check_campaign_exists_by_email(self, email: str) -> bool:
        """
        Check Campaigns Exist by Email
        """
        return self.list_campaigns().filter(email=email).exists()

    def check_campaign_exists_by_master_user(self, master_user_id: uuid.UUID) -> bool:
        """
        Check Campaigns Exist by Master User ID
        """
        return self.list_campaigns().filter(master_user_id=master_user_id).exists()

    def check_campaign_owner_by_email(self, login_user_id: uuid.UUID, email: str) -> bool:
        """
        Check Campaigns Owner by Email and Login User ID(MasterUser or User)
        """
        try:
            campaign = self.get_campaign_by_email(email=email)
            if campaign.master_user_id == login_user_id or campaign.user_id == login_user_id:
                return True
            return False
        except Exception as e:
            raise e

    def encrypt_app_password(self, app_password: str) -> Union[str, None]:
        """
        Encrypt App Password
        """
        encrypted_app_password = None
        if app_password:
            encrypted_app_password = SecretEncryption().encrypt_secret_string(string=app_password)
        return encrypted_app_password

    def decrypt_app_password(self, encrypted_app_password: str) -> Union[str, None]:
        """
        Decrypt App Password
        """
        app_password = None
        if encrypted_app_password:
            app_password = SecretEncryption().decrypt_secret_string(encrypted_string=encrypted_app_password)
        return app_password

    def check_validation_of_email_and_app_password(self, email_provider: str, email: str, app_password: str) -> bool:
        """
        Check Email Provider, Email and App Password Validation by Authenticating SMTP Login
        """
        try:
            SMTPServices(email_provider=email_provider, username=email,
                         app_password=app_password).set_smtp_server_configurations()
            return True
        except Exception as e:
            raise InvalidCredentialsException(
                message="Invalid Configurations. Enter Proper Email Provider, Email, App Password",
                item={'error_tag': 'common', 'error': e.args})

    def validate_email_and_check_campaign_exist(self, data_dict: dict) -> bool:
        """
        Check for Email Validation and Check Campaign Email is Exist
        """
        email = data_dict.get('email')
        user = data_dict.get('user')

        if not validate_email_by_regex(email):
            raise ValidationException(message="Please, Enter Valid Email.", item={'error_tag': 'email'})

        if self.check_campaign_exists_by_email(email=email) or (
                email != user.email and UserAppServices().check_user_email_exists(email=email)):
            raise CampaignAlreadyExist(message=f"Email Campaign already exist on {email}.",
                                       item={'error_tag': 'common'})
        return True

    def create_campaign_by_dict(self, data_dict: dict) -> Campaign:
        """
        Creates Campaigns by Email, Email Provider, App Password
        """
        email = data_dict.get('email')
        email_provider = data_dict.get('email_provider')
        selected_flow = data_dict.get('selected_flow')
        app_password = data_dict.get('app_password', None)
        master_user_id = data_dict.get('master_user_id')

        user_id = None
        action_required_for_campaign = CampaignActionRequiredChoices.PAYMENT_AND_APP_PASSWORD_BOTH_REQUIRED

        if not validate_email_by_regex(email):
            raise ValidationException(message="Please, Enter Valid Email.", item={'error_tag': 'email'})

        if self.check_campaign_exists_by_email(email=email):
            raise CampaignAlreadyExist(message="Email Campaign already exist.", item={'error_tag': 'common'})

        if selected_flow == 'inbox':
            user_id = master_user_id
            action_required_for_campaign = CampaignActionRequiredChoices.PAYMENT_REQUIRED

            try:
                # Validate Email and App password using SMTP Authentication
                self.check_validation_of_email_and_app_password(email_provider=email_provider, email=email,
                                                                app_password=app_password)
            except Exception as e:
                raise InvalidCredentialsException(
                    message="Invalid Configurations. Enter Proper Email Provider, Email, App Password.",
                    item={'error_tag': 'common', 'error': e.args})

        try:
            encrypted_app_password = self.encrypt_app_password(app_password=app_password)
            campaign_data = CampaignData(email=email, email_service_provider=email_provider,
                                         app_password=encrypted_app_password,
                                         master_user_id=master_user_id, user_id=user_id,
                                         action_required=action_required_for_campaign)
            campaign = self.campaign_services.get_campaign_factory().build_entity_with_id(
                campaign_data=campaign_data)
            campaign.save()
            return campaign
        except Exception as e:
            raise CampaignCreationException(message="Something went wrong while creating Campaign.",
                                            item={'error_tag': 'common', 'error': e.args})

    def update_campaign_by_app_password_for_joining_flow(self, data_dict: dict) -> None:
        """
        Check Email and App password and Update App Password in Campaign
        """
        email = data_dict.get('email')
        app_password = data_dict.get('app_password')

        try:
            # Get Campaign Instance
            campaign_instance = CampaignAppServices().get_campaign_by_email(email=email)
        except Exception as e:
            raise e

        try:
            # Validate Email and App password using SMTP Authentication
            self.check_validation_of_email_and_app_password(email_provider=campaign_instance.email_service_provider,
                                                            email=email, app_password=app_password)
        except Exception as e:
            raise InvalidCredentialsException(
                message="Invalid Configurations. Enter Proper App Password",
                item={'error_tag': 'common', 'error': e.args})

        encrypted_app_password = self.encrypt_app_password(app_password=app_password)
        campaign_instance.app_password = encrypted_app_password
        campaign_instance.save()
        return None

    def create_invitation_link_and_send_mail_to_invitee(self, master_user_id: str, warmup_email: str,
                                                        current_site: str) -> None:
        """
        Creates Invitation link and Send Mail to Warmup Email ID
        """
        try:
            master_user = UserAppServices().get_user_by_id(id=master_user_id)
            expiration_time = (datetime.datetime.now() + datetime.timedelta(days=4)).strftime("%d-%m-%y %H:%M:%S")
            invitation_link_token = str(master_user_id) + "break_point" + warmup_email + "break_point" + expiration_time
            encoded_invitation_token = encode_by_base64(string=invitation_link_token)
            invitation_link = f"http://{current_site}/onboarding/?token={encoded_invitation_token}"

            sendgrid_invitation_link_template_id = getattr(settings, "SENDGRID_INVITATION_LINK_TEMPLATE_KEY", None)
            username = warmup_email.split('@')[0]
            master_user_username = master_user.first_name if master_user.first_name else master_user.email.split('@')[0]
            template_data = {
                'username': username,
                'master_user_username': master_user_username,
                'invitation_link': invitation_link
            }
            sendgrid_mail(to_email=warmup_email, TEMPLATE_KEY=sendgrid_invitation_link_template_id,
                          dynamic_data_for_template=template_data)
        except Exception as e:
            raise e

    def update_campaign_by_emails_per_day_and_step_up(self, data_dict: dict) -> Campaign:
        """
        Update Campaign Data (Max. Emails/Day and Step Up)
        """
        selected_flow = data_dict.get('selected_flow')
        master_user_id = data_dict.get('master_user_id')
        is_master_user = data_dict.get('is_master_user')
        current_site = data_dict.get('current_site')
        warmup_email = data_dict.get('warmup_email')
        selected_campaign_type = data_dict.get('campaign_type')

        if master_user_id:
            is_master_user = True

        campaign_type_instance = CampaignAppServices().get_campaign_type_by_name(name=selected_campaign_type)

        # Get default Values of Max Emails/Day and Step up by Selected Campaign Type
        max_emails_per_day = campaign_type_instance.max_emails_per_day
        step_up = campaign_type_instance.step_up
        starting_mails = campaign_type_instance.starting_mails

        if selected_campaign_type == 'custom':
            try:
                max_emails_per_day = int(data_dict.get('max_emails_per_day'))
                step_up = int(data_dict.get('step_up'))
            except Exception:
                raise CampaignDataValidation(message="Emails per day and step up must be positive integer.",
                                             item={'error_tag': 'data_not_validated'})
            if not (max_emails_per_day > 0 and step_up > 0):
                raise CampaignDataValidation(message="Emails per day and step up must be positive integer.",
                                             item={'error_tag': 'data_not_validated'})

        try:
            campaign = self.get_campaign_by_email(email=warmup_email)
            campaign.domain_type = selected_campaign_type
            campaign.mails_to_be_sent = int(starting_mails)
            campaign.max_email_per_day = int(max_emails_per_day)
            campaign.email_step_up = int(step_up)
            # Update Require Action
            if not campaign.app_password:
                campaign.action_required = CampaignActionRequiredChoices.APP_PASSWORD_REQUIRED
            else:
                campaign.action_required = CampaignActionRequiredChoices.NONE

            # Update is_stopped of Campaign
            if not is_master_user or (selected_flow == 'inbox' and is_master_user):
                campaign.is_stopped = False
            campaign.save()

            if selected_flow == 'invite' and master_user_id is not None:
                self.create_invitation_link_and_send_mail_to_invitee(master_user_id=master_user_id,
                                                                     warmup_email=warmup_email,
                                                                     current_site=current_site)
            return campaign

        except Exception as e:
            raise e

    def update_campaign_by_campaign_running_status_is_stopped(self, data_dict: dict) -> Campaign:
        """
        Toggle(True/False) Campaign status(is_stopped)
        """
        try:
            campaign_id = data_dict.get('campaign_id')
            user = data_dict.get('user')
            campaign = self.get_campaign_by_id(id=uuid.UUID(campaign_id))
            if not campaign.plan_id:
                raise ActionRequiredException(message="Payment Required.", item={'error_tag': 'payment_required'})
            if not (campaign.app_password and campaign.max_email_per_day and campaign.email_step_up):
                if not user.is_master_user:
                    raise ActionRequiredException(message="Complete Required Steps to Start Warmup.",
                                                  item={'error_tag': 'complete_required_steps'})
                raise ActionRequiredException(message="App Password Required.", item={})
            campaign.is_stopped = False if campaign.is_stopped else True
            campaign.save()
            return campaign
        except Exception as e:
            raise e

    def get_user_first_name_by_warmup_email(self, warmup_email: str) -> str:
        """
        Get User's FirstName by Warmup Email of Campaign
        """
        try:
            user = UserAppServices().get_user_by_email(email=warmup_email)
            first_name = user.first_name
            if not first_name:
                raise Exception
            return first_name
        except Exception as e:
            raise e

    # =====================================================================================
    # CAMPAIGN TYPES
    # =====================================================================================
    def get_campaign_type_by_id(self, id: UUID) -> CampaignType:
        """
        Get campaign_type instance by id
        """
        try:
            return self.campaign_type_services.get_campaign_type_repo().get(id=id)
        except Exception as e:
            raise CampaignTypeDoesNotExist(message="CampaignType with this id is not registered yet.",
                                           item={'error': e.args})

    def get_campaign_type_by_name(self, name: str) -> CampaignType:
        """
        Get campaign_type instance by name
        """
        try:
            return self.campaign_type_services.get_campaign_type_repo().get(name=name)
        except Exception as e:
            raise CampaignTypeDoesNotExist(message="CampaignType with this name is not registered yet.",
                                           item={'error': e.args})

    def list_campaign_types(self) -> QuerySet[CampaignType]:
        """
        List all campaign_types
        """
        return self.campaign_type_services.get_campaign_type_repo().all()

    # =====================================================================================
    # CAMPAIGN REPORT
    # =====================================================================================

    def get_campaign_report_by_id(self, id: UUID) -> CampaignReport:
        """
        Get campaign_report instance by id
        """
        try:
            return self.campaign_report_services.get_campaign_report_repo().get(id=id)
        except Exception as e:
            raise CampaignReportDoesNotExist(message="CampaignReport does not exist.", item={'error': e.args})

    def list_campaign_reports(self) -> QuerySet[CampaignReport]:
        """
        List all campaign_reports
        """
        return self.campaign_report_services.get_campaign_report_repo().all()

    def list_campaign_reports_by_user_id(self, user_id: uuid.UUID) -> QuerySet[CampaignReport]:

        """
        List campaign_reports by User ID
        """
        return self.list_campaign_reports().filter(user_id=user_id)

    def list_campaign_reports_by_master_user_id(self, master_user_id: uuid.UUID) -> QuerySet[CampaignReport]:

        """
        List campaign_reports by Master User ID
        """
        return self.list_campaign_reports().filter(master_user_id=master_user_id)

    def list_campaign_reports_by_campaign_id(self, campaign_id: uuid.UUID) -> QuerySet[CampaignReport]:

        """
        List campaign_reports by Master User ID
        """
        return self.list_campaign_reports().filter(campaign_id=campaign_id)

    def list_campaign_reports_by_email(self, email: str) -> QuerySet[CampaignReport]:

        """
        List campaign_reports by Email
        """
        return self.list_campaign_reports().filter(email=email)

    def list_campaign_reports_by_record_date(self, start_date: datetime, end_date: datetime) -> QuerySet[
        CampaignReport]:

        """
        List campaign_reports by Start and End Record Date
        """
        return self.list_campaign_reports().filter(record_date__gt=start_date, record_date_lt=end_date)

    def check_campaign_reports_exist_by_report_date_and_campaign_id(self, report_date: datetime.date,
                                                                    campaign_id: uuid.UUID) -> \
            QuerySet[CampaignReport]:

        """
        Check campaign_reports Exist by Report Date and Campaign ID
        """
        campaign_report_exist = self.list_campaign_reports().filter(report_date=report_date,
                                                                    campaign_id=campaign_id).exists()
        return campaign_report_exist

    def read_record_file_to_list_of_dict(self, file_date: str) -> pandas.DataFrame:
        """
        Read Record Log File and Convert it to a List of Dicts
        """
        data_list = list()
        with open(f'logs/records/{file_date}_records.log') as file:
            log_datas = file.readlines()
            for data_line in log_datas:
                log_data = json.loads(data_line)
                data_dict = dict()
                data_dict['sender_name'] = log_data.get('sender').get("name")
                data_dict['sender_email'] = log_data.get('sender').get("email")
                data_dict['sender_email_provider'] = log_data.get('sender').get("email_provider")
                data_dict['sender_send_max_emails_per_day'] = log_data.get('sender').get("send_max_emails_per_day")
                data_dict['sender_total_sent_mails'] = log_data.get('sender').get("total_number_of_sent_mails")
                data_dict['receiver_name'] = log_data.get('receiver').get("name")
                data_dict['receiver_email'] = log_data.get('receiver').get("email")
                data_dict['receiver_email_provider'] = log_data.get('receiver').get("email_provider")
                data_dict['mail_sent_status'] = log_data.get("mail_sent_status")
                data_dict['subject'] = log_data.get("template_subject")
                data_dict['message_id'] = log_data.get("message_id")
                data_dict['thread_number'] = log_data.get("thread_number")
                data_dict['date'] = log_data.get("date")
                data_dict['time'] = log_data.get("time")
                data_dict['datetime'] = log_data.get("datetime")
                data_dict['msg'] = log_data.get("msg")
                data_dict['body'] = log_data.get("body")
                data_list.append(data_dict)
        df = pd.DataFrame(data_list)

        # Filling None values to 0 if it is Integer or Float Field
        df[['sender_send_max_emails_per_day', 'sender_total_sent_mails', 'thread_number']] = df[
            ['sender_send_max_emails_per_day', 'sender_total_sent_mails', 'thread_number']].fillna(value=0)

        # Filling None values to "" if it is String Field
        df[['sender_name', 'sender_email', 'sender_email_provider', 'receiver_name', 'receiver_email',
            'receiver_email_provider', 'mail_sent_status', 'subject', 'message_id', 'date', 'time', 'datetime', 'msg',
            'body']] = df[['sender_name', 'sender_email', 'sender_email_provider', 'receiver_name', 'receiver_email',
                           'receiver_email_provider', 'mail_sent_status', 'subject', 'message_id', 'date', 'time',
                           'datetime', 'msg', 'body']].fillna(value="")
        return df

    def calculate_total_sent_mails_by_sender_email(self, file_date: str, sender_email: str) -> int:
        """
        Calculates Total Number of Sent Mails by Warmup Emails
        """
        try:
            dataframe = self.read_record_file_to_list_of_dict(file_date=file_date)
            if not dataframe.empty:
                filtered_dataframe = dataframe[dataframe['sender_email'] == sender_email]
                total_number_of_sent_mails = int(len(filtered_dataframe))
                if sender_email == "vipul.citrusbug@gmail.com":
                    print(filtered_dataframe)
                return total_number_of_sent_mails
            return 0
        except Exception as e:
            print(e)
            return 0

    def calculate_inbox_and_reputation_ratio_with_email_alerts(self, report_date: datetime.date) -> bool:
        """
        Calculates and Updates Inbox Ratio and Reputation Ratio and Send Email if Reputation goes Down to Threshold Limit
        """
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
                base_url = getattr(settings, "BASE_URL",None)
                # Sending Mail to User
                user = UserAppServices().get_user_by_id(id=campaign_report_instance.user_id)
                username = user.first_name if user.first_name else user.email.split('@')[0]
                template_data = {
                    'username': username,
                    'date_time': report_date.strftime("%Y-%m-%d"),
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
                        'date_time': report_date.strftime("%Y-%m-%d"),
                        'email': campaign_report_instance.email,
                        'login_link': f"{base_url}/onboarding/"
                    }
                    sendgrid_mail(to_email=user.email,
                                  TEMPLATE_KEY=sendgrid_reputation_alert_template_id,
                                  dynamic_data_for_template=template_data)
        return True

    def create_campaign_reports_by_log_records(self) -> bool:
        """
        Creates Campaign Reports
        """
        report_date = (datetime.datetime.now() - datetime.timedelta(days=1)).date()
        # report_date = (datetime.datetime.now()).date()
        file_date = report_date.strftime("%Y-%m-%d")
        # file_date = "2023-09-12"
        raw_df = self.read_record_file_to_list_of_dict(file_date=file_date)
        # TODO : Remove Below 1 line
        # raw_df.to_excel(f"utils/embermail_data_excels/raw_df.xlsx", index=False)
        domain_emails_list = self.list_domain_lists_by_is_active()

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
                    start_date = datetime.datetime(2023, 9, 12).strftime('%d-%b-%Y')
                    end_date = datetime.datetime(2023, 9, 13).strftime('%d-%b-%Y')
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
                    campaign_report_instance, created = self.campaign_report_services.get_campaign_report_factory().get_entity_with_get_or_create(
                        campaign_report_data=campaign_report_data)
                    if not created:
                        campaign_report_instance.total_emails_sent += total_sent_mails
                        campaign_report_instance.inbox_count += inbox_count
                        campaign_report_instance.category_count += category_count
                        campaign_report_instance.spam_count += spam_count
                        campaign_report_instance.save()

        return True

    # =====================================================================================
    # DOMAIN LIST
    # =====================================================================================

    def get_email_domain_by_id(self, id: UUID) -> DomainList:
        """
        Get Email Domain instance by id
        """
        try:
            return self.domain_list_services.get_domain_list_repo().get(id=id)
        except Exception as e:
            raise DomainListDoesNotExist(message="DomainList does not exist.", item={'error': e.args})

    def get_email_domain_by_email(self, email: str) -> DomainList:
        """
        Get Email Domain instance by email
        """
        try:
            return self.domain_list_services.get_domain_list_repo().get(email=email)
        except Exception as e:
            raise DomainListDoesNotExist(message="DomainList does not exist.", item={'error': e.args})

    def list_domain_lists(self) -> QuerySet[DomainList]:
        """
        List all domain_lists
        """
        return self.domain_list_services.get_domain_list_repo().all()

    def list_domain_lists_by_is_active(self) -> QuerySet[DomainList]:

        """
        List domain_lists by is_active True
        """
        return self.list_domain_lists().filter(is_active=True)

    def create_domain_email(self, email: str, email_service_provider: str, app_password: str) -> DomainList:
        """
        Create a domain email by Email, Email Service Provider and App Password
        """
        try:
            encrypted_app_password = self.encrypt_app_password(app_password=app_password)
            domain_list_data = DomainListData(email=email, email_service_provider=email_service_provider,
                                              app_password=encrypted_app_password)
            domain_email = self.domain_list_services.get_domain_list_factory().build_entity_with_id(
                domain_list_data=domain_list_data)
            domain_email.save()
            return domain_email
        except Exception as e:
            raise DomainEmailCreationException(message="Something went wrong in creating Domain Email.",
                                               item={'error': e.args})

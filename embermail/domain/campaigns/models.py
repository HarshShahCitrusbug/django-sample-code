import uuid
from datetime import datetime
from typing import Union, Tuple
from dataclasses import dataclass

from django.db import models
from django.core.validators import validate_email
from dataclass_type_validator import dataclass_validate
from embermail.domain.text_choices import EmailServiceProviderChoices, CampaignActionRequiredChoices, DomainTypes

from utils.django import custom_models
from utils.data_manipulation.type_conversion import encode_by_base64, decode_by_base64
from utils.data_manipulation.type_conversion import as_dict


@dataclass_validate(before_post_init=True)
@dataclass(frozen=True)
class CampaignData:
    """
    Campaign data which is passed to the CampaignFactory
    """
    email: str
    master_user_id: Union[uuid.UUID, None] = None
    user_id: Union[uuid.UUID, None] = None
    app_password: Union[str, None] = None
    email_service_provider: Union[str, None] = None
    domain_type: Union[str, None] = None
    mails_to_be_sent: int = 2
    max_email_per_day: Union[int, None] = None
    email_step_up: Union[int, None] = None
    plan_id: Union[uuid.UUID, None] = None
    next_invoice_date: Union[datetime.date, None] = None
    is_stopped: bool = True
    is_cancelled: bool = False
    action_required: str = CampaignActionRequiredChoices.PAYMENT_AND_APP_PASSWORD_BOTH_REQUIRED

    def __post_init__(self):
        validate_email(self.email)


class Campaign(custom_models.ActivityTracking):
    """
    Campaign Model with ActivityTracking model
    """

    id = models.UUIDField(editable=False, primary_key=True, default=uuid.uuid4)
    master_user_id = models.UUIDField(max_length=64, null=True, blank=True)
    user_id = models.UUIDField(max_length=64, null=True, blank=True)
    email = models.EmailField(max_length=64, unique=True)
    app_password = models.CharField(max_length=255, null=True, blank=True)
    email_service_provider = models.CharField(max_length=55, choices=EmailServiceProviderChoices.choices)
    domain_type = models.CharField(max_length=55, choices=DomainTypes.choices, default=DomainTypes.MAINTAIN)
    mails_to_be_sent = models.IntegerField(null=True, blank=True, default=2)
    max_email_per_day = models.IntegerField(null=True, blank=True)
    email_step_up = models.IntegerField(null=True, blank=True)
    is_stopped = models.BooleanField(default=True)
    is_cancelled = models.BooleanField(default=False)
    plan_id = models.UUIDField(max_length=64, null=True, blank=True)
    next_invoice_date = models.DateField(null=True, blank=True)
    action_required = models.CharField(max_length=55, choices=CampaignActionRequiredChoices.choices,
                                       default=CampaignActionRequiredChoices.PAYMENT_AND_APP_PASSWORD_BOTH_REQUIRED,
                                       null=True, blank=True)

    class Meta:
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"
        db_table = "campaign"

    def __str__(self):
        return self.email


class CampaignFactory:
    @staticmethod
    def build_entity_with_id(campaign_data: CampaignData) -> Campaign:
        """
        Factory method used for build an instance of Campaign
        """
        campaign_data_dict = as_dict(campaign_data, skip_empty=True)
        return Campaign(id=uuid.uuid4(), **campaign_data_dict)


class CampaignType(custom_models.ActivityTracking):
    """
    Campaign Domain Types with ActivityTracking model
    """

    id = models.UUIDField(editable=False, primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=55, choices=DomainTypes.choices, default=DomainTypes.MAINTAIN)
    display_name = models.CharField(max_length=55, null=True, blank=True, default="")
    max_emails_per_day = models.IntegerField(null=True, blank=True)
    step_up = models.IntegerField(null=True, blank=True)
    starting_mails = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "CampaignType"
        verbose_name_plural = "CampaignTypes"
        db_table = "campaign_type"

    def __str__(self):
        return self.name


@dataclass_validate(before_post_init=True)
@dataclass(frozen=True)
class CampaignReportData:
    """
    CampaignReport data which is passed to the CampaignReportFactory
    """
    email: str
    spam_count: int
    inbox_count: int
    report_date: datetime.date
    category_count: int
    total_emails_sent: int
    campaign_id: uuid.UUID
    master_user_id: Union[uuid.UUID, None] = None
    user_id: Union[uuid.UUID, None] = None

    def __post_init__(self):
        validate_email(self.email)


class CampaignReport(custom_models.ActivityTracking):
    """
    CampaignReport Model with ActivityTracking model
    """

    id = models.UUIDField(editable=False, primary_key=True, default=uuid.uuid4)
    report_date = models.DateField()
    master_user_id = models.UUIDField(max_length=64, null=True, blank=True)
    user_id = models.UUIDField(max_length=64, null=True, blank=True)
    campaign_id = models.UUIDField(max_length=64)
    email = models.EmailField(max_length=64)
    total_emails_sent = models.IntegerField(default=0)
    spam_count = models.IntegerField(default=0)
    inbox_count = models.IntegerField(default=0)
    category_count = models.IntegerField(default=0)
    inbox_ratio = models.FloatField(null=True, blank=True, default=0)
    reputation_ratio = models.FloatField(null=True, blank=True, default=0)

    class Meta:
        verbose_name = "CampaignReport"
        verbose_name_plural = "CampaignReports"
        db_table = "campaign_report"

    def __str__(self):
        return f"{self.id} - {self.email}"


class CampaignReportFactory:
    @staticmethod
    def build_entity_with_id(campaign_report_data: CampaignReportData) -> CampaignReport:
        """
        Factory method used for build an instance of CampaignReport
        """
        campaign_report_data_dict = as_dict(campaign_report_data, skip_empty=True)
        return CampaignReport(id=uuid.uuid4(), **campaign_report_data_dict)

    @staticmethod
    def get_entity_with_get_or_create(campaign_report_data: CampaignReportData) -> Tuple[CampaignReport, bool]:
        """
        Factory method used for build or get an instance of CampaignReport
        """
        campaign_report_data_dict = as_dict(campaign_report_data, skip_empty=True)
        campaign_report_instance, created = CampaignReport.objects.get_or_create(
            email=campaign_report_data_dict.pop("email"), report_date=campaign_report_data_dict.pop("report_date"),
            defaults=campaign_report_data_dict)
        return campaign_report_instance, created


@dataclass_validate(before_post_init=True)
@dataclass(frozen=True)
class DomainListData:
    """
    DomainList data which is passed to the DomainListFactory
    """
    email: str
    app_password: str
    email_service_provider: str
    is_active: bool = True

    def __post_init__(self):
        validate_email(self.email)


class DomainList(custom_models.ActivityTracking):
    """
    DomainList Model Used for Receiving Mails from Warmup Emails
    """
    id = models.UUIDField(editable=False, primary_key=True, default=uuid.uuid4)
    email = models.EmailField(max_length=64)
    app_password = models.CharField(max_length=255)
    email_service_provider = models.CharField(max_length=55)

    class Meta:
        verbose_name = "DomainList"
        verbose_name_plural = "DomainLists"
        db_table = "domain_list"

    def __str__(self):
        return self.email


class DomainListFactory:
    @staticmethod
    def build_entity_with_id(domain_list_data: DomainListData) -> DomainList:
        """
        Factory method used for build an instance of DomainList
        """
        domain_list_data_dict = as_dict(domain_list_data, skip_empty=True)
        return DomainList(id=uuid.uuid4(), **domain_list_data_dict)

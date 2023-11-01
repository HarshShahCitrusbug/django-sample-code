from typing import Type

from django.db.models.manager import BaseManager

from embermail.domain.campaigns.models import Campaign, CampaignFactory, CampaignType, CampaignReportFactory, \
    CampaignReport, DomainList, DomainListFactory


class CampaignServices:
    @staticmethod
    def get_campaign_factory() -> Type[CampaignFactory]:
        return CampaignFactory

    @staticmethod
    def get_campaign_repo() -> BaseManager[Campaign]:
        return Campaign.objects


class CampaignTypeServices:
    @staticmethod
    def get_campaign_type_repo() -> BaseManager[CampaignType]:
        return CampaignType.objects


class CampaignReportServices:
    @staticmethod
    def get_campaign_report_factory() -> Type[CampaignReportFactory]:
        return CampaignReportFactory

    @staticmethod
    def get_campaign_report_repo() -> BaseManager[CampaignReport]:
        return CampaignReport.objects


class DomainListServices:
    @staticmethod
    def get_domain_list_factory() -> Type[DomainListFactory]:
        return DomainListFactory

    @staticmethod
    def get_domain_list_repo() -> BaseManager[DomainList]:
        return DomainList.objects
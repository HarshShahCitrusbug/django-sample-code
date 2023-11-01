from django.contrib import admin

from embermail.domain.campaigns.models import Campaign, CampaignType, CampaignReport, DomainList


class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        'email', 'master_user_id', 'user_id', 'email_service_provider', 'mails_to_be_sent', 'max_email_per_day',
        'email_step_up', 'is_stopped', 'is_cancelled')
    search_fields = ('id', 'email', 'master_user_id', 'user_id')
    list_filter = ('email_service_provider', 'is_stopped')


class CampaignTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'display_name', 'max_emails_per_day', 'step_up', 'starting_mails',)
    search_fields = ('name', 'id', 'display_name',)


class CampaignReportAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'report_date', 'email', 'master_user_id', 'user_id', 'campaign_id', 'total_emails_sent', 'inbox_count',
        'category_count', 'spam_count', 'inbox_ratio', 'reputation_ratio')
    search_fields = ('id', 'email', 'master_user_id', 'user_id', 'campaign_id', 'report_date')
    list_filter = ('report_date',)


class DomainListAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'email_service_provider', 'is_active')
    search_fields = ('id', 'email', 'email_service_provider')
    list_filter = ('email_service_provider', 'is_active')
    ordering = ('is_active',)


admin.site.register(Campaign, CampaignAdmin)
admin.site.register(CampaignType, CampaignTypeAdmin)
admin.site.register(CampaignReport, CampaignReportAdmin)
admin.site.register(DomainList, DomainListAdmin)

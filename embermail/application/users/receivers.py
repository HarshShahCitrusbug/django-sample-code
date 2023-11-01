from django.db import transaction
from django.dispatch import receiver

from embermail.application.campaigns.services import CampaignAppServices
from embermail.application.users.signals import user_registered_signal
from embermail.application.users.services import UserAppServices


@receiver(user_registered_signal, sender=UserAppServices)
def receiver_of_user_registered_signal(sender, user, current_site, **kwargs):
    # TODO : Add below functions into @shared_task (CELERY)
    # Run Method - 1
    if user.is_master_user:
        with transaction.atomic():
            UserAppServices().create_and_send_verification_link(current_site=current_site, user=user)

    # Run Method - 2
    if not user.is_master_user:
        with transaction.atomic():
            campaign = CampaignAppServices().get_campaign_by_email(email=user.email)
            campaign.user_id = user.id
            campaign.save()

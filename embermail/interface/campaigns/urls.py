from django.urls import path

from embermail.interface.campaigns import views

app_name = "campaigns"
urlpatterns = [
    # Select Inbox, Email Provider, Add Email and App Password
    path('list/', views.CampaignListView.as_view(), name='list'),
    path('list/search/', views.CampaignListWithSearchView.as_view(), name='campaign_search_list'),
    path('ready-to-start/', views.ReadyToStartView.as_view(), name='ready_to_start'),
    path('select-provider/', views.SelectProviderView.as_view(), name='select_provider'),
    path('add-email/', views.AddEmailView.as_view(), name='add_email'),
    path('imap-access-details/', views.ImapAccessDetailView.as_view(), name='imap_details'),
    path('joining/flow/imap-access-details/', views.JoiningImapAccessDetailView.as_view(), name='joining_imap_details'),
    path('app-password/', views.AddAppPasswordView.as_view(), name='app_password'),
    path('joining/flow/app-password/', views.JoiningAddAppPasswordView.as_view(), name='joining_app_password'),

    # Update Campaign Data (Max. Emails per Day and Step up)
    path('update/', views.UpdateCampaignView.as_view(), name='update_campaign'),
    path('joining/flow/update/', views.JoiningUpdateCampaignView.as_view(), name='joining_update_campaign'),

    # Cancel and Upgrade Subscription
    path('cancel/subscription/', views.CancelSubscriptionView.as_view(), name='cancel_subscription'),

    # Send Invitation Link manually
    path('send-invitation-link/<str:hidden_text>/', views.SendInvitationLinkView.as_view(), name='send_invitation'),

    # Celery Views for Testing
    path('celery/', views.CeleryMailView.as_view(), name='celery_view'),
    path('celery-data/', views.CeleryMailDataView.as_view(), name='celery_data_view'),
    path('reports/', views.CampaignReportView.as_view(), name='campaign_report'),
]

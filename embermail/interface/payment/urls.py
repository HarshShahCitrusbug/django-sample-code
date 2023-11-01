from django.urls import path

from embermail.interface.payment import views

app_name = 'payment'
urlpatterns = [
    path('payment/plan/selection/', views.PlanSelectionView.as_view(), name='plan_selection'),
    path('payment/complete/', views.CompletePaymentView.as_view(), name='complete_payment'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
]

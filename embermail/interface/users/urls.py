from django.urls import path

from embermail.interface.users import views

app_name = 'users'
urlpatterns = [
    # Onboarding (Signup + Login + Logout)
    path('onboarding/', views.OnboardingView.as_view(), name='onboarding'),
    path('onboarding/signup/', views.OnboardingSignupView.as_view(), name='signup'),
    path('onboarding/login/', views.OnboardingLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Home
    path('home/', views.home, name='home'),
    # Contact Us
    path('contact/', views.ContactUsView.as_view(), name="contact"),

    # Email Verification
    path('users/email/verification/<str:encoded_user_id>/', views.user_email_verification, name='email_verification'),

    # Reset Forgot Password
    path('password-reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('reset-password-confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # 404
    path('page-not-found/', views.error_404_page_view, name='404'),
]

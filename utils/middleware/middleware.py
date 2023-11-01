from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import logout


class AdminMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request, pk=None, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_staff and request.user.is_superuser:
                return self.get_response(request, pk) if pk else self.get_response(request)
            messages.error(request, "Access Denied.")
            logout(request)
            return redirect("users:onboarding")
        return redirect("users:onboarding")


class MasterUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request, pk=None, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_master_user:
                return self.get_response(request, pk) if pk else self.get_response(request)
            messages.error(request, "Access Denied.")
            logout(request)
            return redirect("users:onboarding")
        return redirect("users:onboarding")
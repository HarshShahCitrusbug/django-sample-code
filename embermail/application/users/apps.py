from django.apps import AppConfig


class ApplicationUsersConfig(AppConfig):
    name = "embermail.application.users"
    label = "application_users"

    def ready(self):
        # Implicitly connect signal handlers decorated with @receiver.
        from embermail.application.users import receivers
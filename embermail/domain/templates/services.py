from typing import Type

from django.db.models.manager import BaseManager

from embermail.domain.templates.models import Template, TemplateFactory, ThreadFactory, Thread


class TemplateServices:
    @staticmethod
    def get_template_factory() -> Type[TemplateFactory]:
        return TemplateFactory

    @staticmethod
    def get_template_repo() -> BaseManager[Template]:
        return Template.objects


class ThreadServices:
    @staticmethod
    def get_thread_factory() -> Type[ThreadFactory]:
        return ThreadFactory

    @staticmethod
    def get_thread_repo() -> BaseManager[Thread]:
        return Thread.objects

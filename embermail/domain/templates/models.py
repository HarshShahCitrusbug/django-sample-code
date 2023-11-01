import uuid
from typing import Union, Tuple
from dataclasses import dataclass

from django.db import models

from utils.django import custom_models
from utils.data_manipulation.type_conversion import as_dict


@dataclass(frozen=True)
class TemplateData:
    """
    Template data which is passed to the TemplateFactory
    """
    name: str
    subject: str
    warmup_email: Union[str, None] = None
    user_id: Union[uuid.UUID, None] = None
    master_user_id: Union[uuid.UUID, None] = None
    is_selected: bool = False
    is_general: bool = False


@dataclass(frozen=True)
class ThreadData:
    """
    Thread data which is passed to the ThreadFactory
    """
    template_id: uuid.UUID
    body: str
    thread_ordering_number: int


class Template(custom_models.ActivityTracking):
    """
    Template Model with ActivityTracking model
    """

    id = models.UUIDField(editable=False, primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=155)
    subject = models.CharField(max_length=155)
    warmup_email = models.CharField(max_length=100, null=True, blank=True)
    user_id = models.UUIDField(null=True, blank=True)
    master_user_id = models.UUIDField(null=True, blank=True)
    is_selected = models.BooleanField(default=False)
    is_general = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Template"
        verbose_name_plural = "Templates"
        db_table = "template"

    def __str__(self):
        return self.name


class Thread(custom_models.ActivityTracking):
    """
    Thread Model with ActivityTracking model
    """

    id = models.UUIDField(editable=False, primary_key=True, default=uuid.uuid4)
    template_id = models.UUIDField()
    body = models.TextField()
    thread_ordering_number = models.IntegerField()

    class Meta:
        verbose_name = "Thread"
        verbose_name_plural = "Threads"
        db_table = "thread"

    def __str__(self):
        return str(self.template_id)


class TemplateFactory:
    @staticmethod
    def build_entity_with_id(template_data: TemplateData) -> Template:
        """
        Factory method used for build an instance of Template
        """
        template_data_dict = as_dict(template_data, skip_empty=True)
        return Template(id=uuid.uuid4(), **template_data_dict)

    @staticmethod
    def get_entity_with_get_or_create(template_data: TemplateData) -> Tuple[Template, bool]:
        """
        Factory method used for build or get an instance of Template
        """
        template_data_dict = as_dict(template_data, skip_empty=True)
        template_instance, created = Template.objects.get_or_create(name=template_data_dict.pop("name"),
                                                                    warmup_email=template_data_dict.pop("warmup_email"),
                                                                    defaults=template_data_dict)
        return template_instance, created


class ThreadFactory:
    @staticmethod
    def build_entity_with_id(thread_data: ThreadData) -> Thread:
        """
        Factory method used for build an instance of Thread
        """
        thread_data_dict = as_dict(thread_data, skip_empty=True)
        return Thread(id=uuid.uuid4(), **thread_data_dict)

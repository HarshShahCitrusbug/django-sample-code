import uuid

from uuid import UUID

from django.db.models import Q
from django.db import transaction
from django.db.models.query import QuerySet

from embermail.domain.templates.models import Thread, Template, TemplateData, ThreadData
from utils.django.exceptions import TemplateDoesNotExist, ThreadDoesNotExist, TemplateThreadAccessDenied, \
    TemplateAlreadyExist
from embermail.domain.templates.services import ThreadServices, TemplateServices


class TemplateAppServices:
    template_services = TemplateServices()
    thread_services = ThreadServices()

    # =====================================================================================
    # TEMPLATE
    # =====================================================================================

    def get_template_by_id(self, id: UUID) -> Template:
        """
        Get template instance by id
        """
        try:
            return self.template_services.get_template_repo().get(id=id)
        except Exception as e:
            raise TemplateDoesNotExist(message="Template not Found.", item={'error': e.args})

    def get_template_by_name(self, name: str) -> Template:
        """
        Get template instance by name
        """
        try:
            return self.template_services.get_template_repo().get(name=name)
        except Exception as e:
            raise TemplateDoesNotExist(message="Template not Found.", item={'error': e.args})

    def get_template_by_subject(self, subject: str) -> Template:
        """
        Get template instance by subject
        """
        try:
            return self.template_services.get_template_repo().get(subject=subject)
        except Exception as e:
            raise TemplateDoesNotExist(message="Template not Found.", item={'error': e.args})

    def list_templates(self) -> QuerySet[Template]:
        """
        List all templates
        """
        return self.template_services.get_template_repo().all()

    def list_templates_by_user_id(self, user_id: str) -> QuerySet[Template]:
        """
        List templates by User ID
        """
        return self.list_templates().filter(user_id=user_id)

    def check_template_name_is_unique_by_warmup_email(self, template_name: str, warmup_email: str) -> bool:
        """
        Checks Template Name is Exist with a Warmup Email
        """
        return self.list_templates().filter(
            Q(name=template_name) & Q(Q(warmup_email=warmup_email) | Q(warmup_email__isnull=True))).exists()

    def create_template_by_name_and_subject(self, template_data_dict: dict) -> Template:
        """
        Creates Template by Using Template's Name and Subject
        """
        try:
            template_name = template_data_dict.get('template_name')
            template_subject = template_data_dict.get('template_subject')
            warmup_email = template_data_dict.get('warmup_email')
            user_id = template_data_dict.get('user_id')
            master_user_id = template_data_dict.get('master_user_id')
            is_general = template_data_dict.get('is_general', False)

            if self.check_template_name_is_unique_by_warmup_email(template_name=template_name,
                                                                  warmup_email=warmup_email):
                message = "Template name must be unique."
                raise TemplateAlreadyExist(message=message, item={'error_tag': 'common'})

            is_selected = False
            if warmup_email:
                is_selected = True
            template_data = TemplateData(name=template_name, subject=template_subject, warmup_email=warmup_email,
                                         user_id=user_id, master_user_id=master_user_id, is_selected=is_selected,
                                         is_general=is_general)
            template_instance = self.template_services.get_template_factory().build_entity_with_id(
                template_data=template_data)
            template_instance.save()
            return template_instance
        except Exception as e:
            raise e

    def update_status_of_template_is_selected(self, template_id: str, warmup_email: str, user_id: str,
                                              master_user_id: str) -> None:
        """
        Change The is_selected status of Template
        """
        try:
            template_instance = self.get_template_by_id(id=uuid.UUID(template_id))
            if template_instance.warmup_email == warmup_email or (
                    template_instance.warmup_email == warmup_email and template_instance.master_user_id == master_user_id):
                if template_instance.is_selected:
                    template_instance.is_selected = False
                else:
                    template_instance.is_selected = True
                template_instance.save()
                return None
            raise TemplateThreadAccessDenied(message="Access Denied.",
                                             item={"error": 'Access Denied while Updating Template Status.'})
        except Exception as e:
            raise e

    def update_template_by_name_and_subject(self, template_data_dict: dict) -> None:
        """
        Updates Template's Name and Subject
        """
        try:
            template_id = template_data_dict.get("template_id")
            name = template_data_dict.get("name")
            subject = template_data_dict.get("subject")
            warmup_email = template_data_dict.get("warmup_email")
            user_id = template_data_dict.get("user_id")
            master_user_id = template_data_dict.get("master_user_id")
            template_instance = self.get_template_by_id(id=uuid.UUID(template_id))
            if template_instance.warmup_email == warmup_email or (
                    template_instance.warmup_email == warmup_email and template_instance.master_user_id == master_user_id):
                if not template_instance.name == name:
                    if self.check_template_name_is_unique_by_warmup_email(template_name=name,
                                                                          warmup_email=warmup_email):
                        message = "Template name must be unique."
                        raise TemplateAlreadyExist(message=message, item={'error_tag': 'common'})
                    template_instance.name = name
                if not template_instance.subject == subject:
                    template_instance.subject = subject
                template_instance.save()
                return None
            raise TemplateThreadAccessDenied(message="Access Denied.",
                                             item={"error": 'Access Denied in Updating Template.'})
        except Exception as e:
            raise e

    def delete_template_by_template_id(self, template_id: str, warmup_email: str, user_id: str,
                                       master_user_id: str) -> None:
        """
        Delete Template by Template ID
        """
        try:
            template_instance = self.get_template_by_id(id=uuid.UUID(template_id))
            if template_instance.warmup_email == warmup_email or (
                    template_instance.warmup_email == warmup_email and template_instance.master_user_id == master_user_id):
                with transaction.atomic():
                    self.list_threads_by_template_id(template_id=uuid.UUID(template_id)).delete()
                    template_instance.delete()
                    return None
            raise TemplateThreadAccessDenied(message="Access Denied.",
                                             item={"error": 'Access Denied in Deleting Template.'})
        except Exception as e:
            raise e

    def add_default_template_to_user_templates(self, default_template_id: str, warmup_email: str, user_id: uuid.UUID,
                                               master_user_id: uuid.UUID) -> bool:
        """
        Add Default Template to User Template by Template ID and User ID
        """
        try:
            default_template_instance = self.get_template_by_id(id=uuid.UUID(default_template_id))
            if default_template_instance.user_id is None:
                # Create Template for User
                template_name = default_template_instance.name
                template_subject = default_template_instance.subject
                template_data = TemplateData(name=template_name, subject=template_subject, warmup_email=warmup_email,
                                             user_id=user_id, master_user_id=master_user_id, is_selected=True)
                template_instance, created = self.template_services.get_template_factory().get_entity_with_get_or_create(
                    template_data=template_data)
                if created:
                    # Create Threads for new Created Template
                    default_threads_list = self.list_threads_by_template_id(template_id=uuid.UUID(default_template_id))
                    threads_list = []
                    for thread in default_threads_list:
                        thread_data = ThreadData(template_id=template_instance.id, body=thread.body,
                                                 thread_ordering_number=thread.thread_ordering_number)
                        thread_instance = self.thread_services.get_thread_factory().build_entity_with_id(
                            thread_data=thread_data)
                        threads_list.append(thread_instance)
                    Thread.objects.bulk_create(threads_list)
                    return True
                return False

        except Exception as e:
            raise e

    # =====================================================================================
    # THREAD
    # =====================================================================================

    def get_thread_by_id(self, id: UUID) -> Thread:
        """
        Get thread instance by id
        """
        try:
            return self.thread_services.get_thread_repo().get(id=id)
        except Exception as e:
            raise ThreadDoesNotExist(message="Thread not Found.", item={'error': e.args})

    def list_threads(self) -> QuerySet[Thread]:
        """
        List all threads
        """
        return self.thread_services.get_thread_repo().all()

    def list_threads_by_template_id(self, template_id: uuid.UUID) -> QuerySet[Thread]:
        """
        List Threads by Template ID
        """
        return self.list_threads().filter(template_id=template_id)

    def list_threads_by_template_name(self, template_name: str) -> QuerySet[Thread]:
        """
        List Threads by Template Name
        """
        return self.list_threads().filter(template_name=template_name)

    def list_threads_by_template_subject(self, template_subject: str) -> QuerySet[Thread]:
        """
        List Threads by Template Subject
        """
        return self.list_threads().filter(template_subject=template_subject)

    def list_threads_by_user_id(self, user_id: uuid.UUID) -> QuerySet[Thread]:
        """
        List Threads by User ID
        """
        return self.list_threads().filter(user_id=user_id)

    def get_thread_count_in_template(self, template_id: uuid.UUID) -> int:
        """
        Returns Total Threads in a Template by Template ID
        """
        return int(self.list_threads_by_template_id(template_id=template_id).count())

    def check_user_can_update_delete_thread(self, template_id: str, user_id: str) -> bool:
        """
        Checking User is Updating, Deleting Own Thread
        """
        template_instance = self.get_template_by_id(id=uuid.UUID(template_id))
        if template_instance.user_id == user_id:
            return True
        return False

    def create_thread_by_template_id_and_body(self, thread_data_dict: dict) -> None:
        """
        Creates Thread by Template ID and Body
        """
        try:
            with transaction.atomic():
                template_id = uuid.UUID(thread_data_dict.get("template_id"))
                body = thread_data_dict.get("body")
                thread_counts = self.get_thread_count_in_template(template_id=template_id)

                thread_data = ThreadData(template_id=template_id, body=body,
                                         thread_ordering_number=int(thread_counts) + 1)
                thread_instance = self.thread_services.get_thread_factory().build_entity_with_id(
                    thread_data=thread_data)
                thread_instance.save()
                return None
        except Exception as e:
            raise e

    def update_thread_by_body(self, thread_data_dict: dict) -> Thread:
        """
        Updates Threads by Body
        """
        try:
            thread_id = thread_data_dict.get("thread_id")
            body = thread_data_dict.get("body")
            template_id = thread_data_dict.get("template_id")
            user_id = thread_data_dict.get("user_id")
            if self.check_user_can_update_delete_thread(template_id=template_id, user_id=user_id):
                thread_instance = self.get_thread_by_id(id=uuid.UUID(thread_id))
                if not thread_instance.body == body:
                    thread_instance.body = body
                    thread_instance.save()
                return thread_instance
            raise TemplateThreadAccessDenied(message="Access Denied.",
                                             item={"error": 'Access Denied in Updating Thread.'})
        except Exception as e:
            raise e

    def delete_thread_by_thread_id(self, thread_data_dict: dict) -> None:
        """
        Delete Thread by Thread ID if it is Last Thread
        """
        try:
            with transaction.atomic():
                thread_id = thread_data_dict.get('thread_id')
                template_id = thread_data_dict.get('template_id')
                user_id = thread_data_dict.get('user_id')
                if self.check_user_can_update_delete_thread(template_id=template_id, user_id=user_id):
                    thread_counts = self.get_thread_count_in_template(template_id=template_id)
                    thread_instance = self.get_thread_by_id(id=uuid.UUID(thread_id))
                    if int(thread_instance.thread_ordering_number) == thread_counts:
                        thread_instance.delete()
                    return None
                raise TemplateThreadAccessDenied(message="Access Denied.",
                                                 item={"error": 'Access Denied in Deleting Thread.'})
        except Exception as e:
            raise e

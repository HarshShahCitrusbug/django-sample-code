import uuid
from typing import Union
from dataclasses import dataclass

from django.core.validators import validate_email
from django.db import models
from dataclass_type_validator import dataclass_validate

from utils.django import custom_models
from embermail.domain.text_choices import PaymentStatusChoices
from utils.data_manipulation.type_conversion import as_dict


@dataclass_validate(before_post_init=True)
@dataclass(frozen=True)
class PlanData:
    """
    Plan data which is passed to the PlanFactory
    """
    name: str
    plan_amount: float
    plan_duration: int
    description: Union[str, None] = None
    stripe_price_id: Union[str, None] = None
    stripe_product_id: Union[str, None] = None


@dataclass_validate(before_post_init=True)
@dataclass(frozen=True)
class PaymentData:
    """
    Payment data which is passed to the PaymentFactory
    """
    warmup_email: str
    master_user_id: uuid.UUID
    purchased_plan_id: uuid.UUID
    invoice_download_url: str
    invoice_name: str
    stripe_subscription: dict
    payment_status: str = PaymentStatusChoices.INCOMPLETE

    def __post_init__(self):
        validate_email(self.warmup_email)


class Plan(custom_models.ActivityTracking):
    """
    Plan Model with ActivityTracking model
    """

    id = models.UUIDField(editable=False, primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=155)
    description = models.CharField(max_length=155, null=True, blank=True)
    plan_amount = models.FloatField()
    plan_duration = models.IntegerField(help_text='in months')
    stripe_price_id = models.CharField(max_length=155, null=True, blank=True)
    stripe_product_id = models.CharField(max_length=155, null=True, blank=True)

    class Meta:
        verbose_name = "Plan"
        verbose_name_plural = "Plans"
        db_table = "plan"

    def __str__(self):
        return self.name


class PaymentMethod(custom_models.ActivityTracking):
    """
    Payment Method Model with ActivityTracking model
    """

    id = models.UUIDField(editable=False, primary_key=True, default=uuid.uuid4)
    user_id = models.CharField(max_length=155)
    stripe_payment_method = models.JSONField()

    class Meta:
        verbose_name = "PaymentMethod"
        verbose_name_plural = "PaymentMethods"
        db_table = "payment_method"

    def __str__(self):
        return self.user_id


class Payment(custom_models.ActivityTracking):
    """
    Payment History Model with Activity Tracking
    """
    id = models.UUIDField(editable=False, default=uuid.uuid4, primary_key=True)
    warmup_email = models.CharField(max_length=101)
    master_user_id = models.UUIDField(editable=False)
    purchased_plan_id = models.UUIDField(editable=False)
    stripe_subscription = models.JSONField()
    invoice_download_url = models.CharField(max_length=555, null=True, blank=True, default="")
    invoice_name = models.CharField(max_length=125, null=True, blank=True, default="")
    payment_status = models.CharField(choices=PaymentStatusChoices.choices, default=PaymentStatusChoices.INCOMPLETE)

    def __str__(self):
        return self.warmup_email


class PlanFactory:
    @staticmethod
    def build_entity_with_id(plan_data: PlanData) -> Plan:
        """
        Factory method used for build an instance of Plan
        """
        plan_data_dict = as_dict(plan_data, skip_empty=True)
        return Plan(id=uuid.uuid4(), **plan_data_dict)


class PaymentMethodFactory:
    @staticmethod
    def build_entity_with_id(user_id: uuid, stripe_payment_method: dict) -> PaymentMethod:
        """
        Factory method used for build an instance of Payment Method
        """
        return PaymentMethod(id=uuid.uuid4(), user_id=user_id, stripe_payment_method=stripe_payment_method)


class PaymentFactory:
    @staticmethod
    def build_entity_with_id(payment_data: PaymentData) -> Payment:
        """
        Factory method used for build an instance of Payment
        """
        payment_data_dict = as_dict(payment_data, skip_empty=True)
        return Payment(id=uuid.uuid4(), **payment_data_dict)

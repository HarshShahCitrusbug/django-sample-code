from typing import Type

from django.db.models.manager import BaseManager

from embermail.domain.payments.models import Plan, PlanFactory, PaymentMethodFactory, PaymentMethod, PaymentFactory, \
    Payment


class PlanServices:
    @staticmethod
    def get_plan_factory() -> Type[PlanFactory]:
        return PlanFactory

    @staticmethod
    def get_plan_repo() -> BaseManager[Plan]:
        return Plan.objects


class PaymentMethodServices:
    @staticmethod
    def get_payment_method_factory() -> Type[PaymentMethodFactory]:
        return PaymentMethodFactory

    @staticmethod
    def get_payment_method_repo() -> BaseManager[PaymentMethod]:
        return PaymentMethod.objects


class PaymentServices:
    @staticmethod
    def get_payment_factory() -> Type[PaymentFactory]:
        return PaymentFactory

    @staticmethod
    def get_payment_repo() -> BaseManager[Payment]:
        return Payment.objects

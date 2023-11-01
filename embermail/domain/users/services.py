from typing import Type

from django.db.models.manager import BaseManager

from embermail.domain.users.models import User, UserFactory, ForgotPassword, ForgotPasswordFactory, VisitedUserFactory, \
    VisitedUser, InquiryFactory, Inquiry


class UserServices:
    @staticmethod
    def get_user_factory() -> Type[UserFactory]:
        return UserFactory

    @staticmethod
    def get_user_repo() -> BaseManager[User]:
        return User.objects


class ForgotPasswordServices:
    @staticmethod
    def get_forgot_password_factory() -> Type[ForgotPasswordFactory]:
        return ForgotPasswordFactory

    @staticmethod
    def get_forgot_password_repo() -> BaseManager[ForgotPassword]:
        return ForgotPassword.objects


class VisitedUserServices:
    @staticmethod
    def get_visited_user_factory() -> Type[VisitedUserFactory]:
        return VisitedUserFactory

    @staticmethod
    def get_visited_user_repo() -> BaseManager[VisitedUser]:
        return VisitedUser.objects


class InquiryServices:
    @staticmethod
    def get_inquiry_factory() -> Type[InquiryFactory]:
        return InquiryFactory

    @staticmethod
    def get_inquiry_repo() -> BaseManager[Inquiry]:
        return Inquiry.objects

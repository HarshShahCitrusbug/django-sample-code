import uuid
from datetime import datetime
from typing import Union, Tuple
from dataclasses import dataclass, field

from django.db import models
from django.core.validators import validate_email
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager, AbstractUser

from dataclass_type_validator import dataclass_validate

from utils.django import custom_models
from utils.data_manipulation.type_conversion import as_dict


@dataclass(frozen=True)
class UserID:
    """
    Value Object (Dataclass) should be used to generate and pass Id to UserFactory
    """

    id: uuid.UUID = field(init=False, default_factory=uuid.uuid4)


@dataclass_validate(before_post_init=True)
@dataclass(frozen=True)
class UserPersonalData:
    """
    User personal data which is passed to the UserFactory
    """
    email: str
    first_name: Union[str, None] = None
    last_name: Union[str, None] = None
    username: Union[str, None] = None
    stripe_customer_id: Union[str, None] = None
    users_master_id: Union[uuid.UUID, None] = None

    def __post_init__(self):
        validate_email(self.email)


@dataclass(frozen=True)
class UserBasePermissions:
    """
    User Base Permissions which is passed to the UserFactory
    """
    is_master_user: bool = True
    is_deleted: bool = False
    is_staff: bool = False
    is_superuser: bool = False
    is_active: bool = True
    is_verified: bool = False


class UserManagerAutoID(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if email is None:
            raise ValueError('Email field is required.')
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        if id not in extra_fields:
            extra_fields = dict(extra_fields, id=UserID().id)

        return self._create_user(username, email, password, **extra_fields)


class User(custom_models.ActivityTracking, AbstractUser):
    """
    User Model with ActivityTracking model
    """
    id = models.UUIDField(editable=False, primary_key=True, default=uuid.uuid4)
    username = models.CharField(max_length=155, null=True, blank=True, unique=False)
    email = models.EmailField(max_length=64, unique=True)
    stripe_customer_id = models.CharField(max_length=64, null=True, blank=True)
    is_master_user = models.BooleanField(default=True)
    users_master_id = models.UUIDField(max_length=64, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    objects = UserManagerAutoID()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "password"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        db_table = "user"

    @property
    def full_name(self):
        """
        Returns "{FirstName} {LastName}"
        """
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.email


class UserFactory:
    @staticmethod
    def build_entity_with_id(password: str, personal_data: UserPersonalData,
                             base_permissions: UserBasePermissions) -> User:
        """
        Factory method used for building an instance of User
        """

        personal_data_dict = as_dict(personal_data, skip_empty=True)
        base_permissions_dict = as_dict(base_permissions, skip_empty=True)
        password = make_password(password=password)
        return User(id=UserID().id, **personal_data_dict, **base_permissions_dict, password=password)


class ForgotPassword(custom_models.ActivityTracking):
    """
    Forgot Password Model
    """
    id = models.UUIDField(editable=False, primary_key=True, default=uuid.uuid4)
    user_id = models.UUIDField(max_length=64)
    password_token = models.CharField(max_length=64, null=True, blank=True)
    password_token_expiry = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.user_id)


class ForgotPasswordFactory:

    @staticmethod
    def build_entity_with_id(user_id: uuid, password_token: Union[str, None] = None,
                             password_token_expiry: Union[datetime, None] = None) -> ForgotPassword:
        """
        Forgot Password Factory method used for build an instance of Forgot Password
        """
        return ForgotPassword(id=uuid.uuid4(), user_id=user_id, password_token=password_token,
                              password_token_expiry=password_token_expiry)

    @staticmethod
    def get_entity_with_get_or_create(user_id: uuid, password_token: str, password_token_expiry: datetime) -> Tuple[
        ForgotPassword, bool]:
        """
        Forgot Password Get or Creates new Instance and return Forgot Password Instance
        """
        forgot_password_instance, created = ForgotPassword.objects.get_or_create(user_id=user_id, defaults={
            'password_token': password_token, 'password_token_expiry': password_token_expiry})
        return forgot_password_instance, created


class VisitedUser(custom_models.ActivityTracking):
    """
    Visited User's Email and IP Address
    """
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    email = models.EmailField(max_length=64)
    ip_address = models.CharField(max_length=55)

    def __str__(self):
        return self.email


class VisitedUserFactory:

    @staticmethod
    def build_entity_with_id(email: str, ip_address: Union[str, None]):
        """
        Visited User Factory method used for build an instance of Visited User
        """
        return VisitedUser(id=uuid.uuid4(), email=email, ip_address=ip_address)


class Inquiry(custom_models.ActivityTracking):
    """
    Contact us Model
    """
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    email = models.EmailField(max_length=64)
    contact_message = models.TextField()
    is_solved = models.BooleanField(default=False)

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "Inquiry"
        verbose_name_plural = "Inquiries"
        db_table = "inquiry"


class InquiryFactory:

    @staticmethod
    def build_entity_with_id(email: str, contact_message: str):
        """
        Inquiry Factory method used for build an instance of Inquiry
        """
        return Inquiry(id=uuid.uuid4(), email=email, contact_message=contact_message)
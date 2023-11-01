import uuid
import datetime
from uuid import UUID
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.db.models.query import QuerySet
from django.utils.timezone import make_aware
from django.contrib.auth import authenticate

from embermail.application.users import signals
from embermail.infrastructure.mailer_sevices.services import sendgrid_mail
from utils.django.regex import validate_email_by_regex, validate_password_by_regex
from utils.data_manipulation.type_conversion import encode_by_base64, decode_by_base64
from embermail.domain.users.services import UserServices, ForgotPasswordServices, VisitedUserServices, InquiryServices
from embermail.domain.users.models import User, ForgotPassword, UserPersonalData, UserBasePermissions, VisitedUser, \
    Inquiry
from utils.django.exceptions import StripeCustomerException, UserDoesNotExist, ForgotPasswordInstanceDoesNotExist, \
    UserAlreadyExist, UserRegistrationException, UserLoginException, InvalidCredentialsException, ValidationException, \
    UserDoesNotVerified, ForgotPasswordException, ForgotPasswordLinkExpired, VisitedUserCreationException, \
    InquiryException, InquiryDoesNotExist


class UserAppServices:
    user_services = UserServices()
    forgot_password_services = ForgotPasswordServices()
    visited_user_services = VisitedUserServices()
    inquiry_services = InquiryServices()

    # =====================================================================================
    # USER
    # =====================================================================================
    def get_user_by_id(self, id: UUID) -> User:
        """
        Get user instance by id
        """
        try:
            return self.user_services.get_user_repo().get(id=id)
        except Exception as e:
            raise UserDoesNotExist(message="User is not registered yet.", item={'error': e.args})

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user instance by email
        """
        try:
            return self.user_services.get_user_repo().get(email=email)
        except Exception as e:
            raise UserDoesNotExist(message="User is not registered yet.", item={'error': e.args})

    def list_users(self) -> QuerySet[User]:
        """
        List all users
        """
        return self.user_services.get_user_repo().all()

    def list_users_by_master_user_id(self, master_user_id: UUID) -> QuerySet[User]:
        """
        List all users have master by master_user_id
        """
        return self.list_users().filter(users_master_id=master_user_id)

    def list_users_by_master_user_email(self, master_user_email: str) -> QuerySet[User]:
        """
        List all users have master by master_user_email
        """
        master_user = self.get_user_by_email(email=master_user_email)
        return self.list_users_by_master_user_id(master_user_id=master_user.id)

    def check_user_email_exists(self, email: str) -> bool:
        return self.list_users().filter(email=email).exists()

    def get_or_create_stripe_customer_id(self, user: User) -> str:
        """
        Get or Create Stripe Customer ID from USER
        """
        from embermail.application.payments.services import StripeAppServices

        try:
            stripe_customer_id = user.stripe_customer_id
            if not stripe_customer_id:
                stripe_customer = StripeAppServices().create_stripe_customer(email=str(user.email),
                                                                             user_id=str(user.id))
                stripe_customer_id = stripe_customer.get('id')
                user.stripe_customer_id = stripe_customer_id
                user.save()
            return stripe_customer_id
        except Exception as e:
            raise e

    def check_user_is_verified(self, email: str) -> bool:
        return self.list_users().filter(email=email, is_verified=True).exists()

    def manually_authenticate_and_login_user(self, email: str, password: str) -> User:
        """
        Manually Login User After Checking Verification
        """
        user_exists = self.check_user_email_exists(email=email)
        if not user_exists:
            raise UserDoesNotExist(message="User with this email is not exists.", item={'error_tag': 'email'})

        user_verified = self.check_user_is_verified(email=email)
        if not user_verified:
            raise UserDoesNotVerified(message="Email verification is required, Check your mails.",
                                      item={'error_tag': 'common'})

        try:
            user = authenticate(email=email, password=password)
            if user is not None:
                return user
            raise InvalidCredentialsException(message="Unable to log in with provided credentials.",
                                              item={'error_tag': 'common'})
        except Exception as e:
            if isinstance(e, InvalidCredentialsException):
                raise e
            raise UserLoginException(message="Something went wrong while Manually Login", item={'error': str(e.args)})

    def create_user_from_dict(self, data: dict) -> User:
        """
        Create user from user's data dict
        """
        email = data.get('email')
        password = data.get('password')
        current_site = data.get('current_site')
        signup_flow_type = data.get('signup_flow')
        master_user_id_for_joining_flow = data.get('master_user_id_for_joining_flow')

        # Email and Password Validation
        if not validate_email_by_regex(email=email):
            custom_error_message = "Please, Enter valid Email."
            raise ValidationException(message=custom_error_message, item={'error_tag': 'email'})
        if not validate_password_by_regex(password=password):
            custom_error_message = "Password should contain at least one digit, lowercase, uppercase, special character and length should be between 8-32."
            raise ValidationException(message=custom_error_message, item={'error_tag': 'password'})

        user_services = self.user_services
        if self.check_user_email_exists(email=email):
            raise UserAlreadyExist(message="this email address already registered", item={'error_tag': 'email'})

        personal_data = UserPersonalData(email=email)
        base_permissions = UserBasePermissions()

        if signup_flow_type == 'join_team':
            personal_data = UserPersonalData(email=email, users_master_id=uuid.UUID(master_user_id_for_joining_flow))
            base_permissions = UserBasePermissions(is_master_user=False, is_verified=True)

        try:
            user = user_services.get_user_factory().build_entity_with_id(password=password,
                                                                         personal_data=personal_data,
                                                                         base_permissions=base_permissions)
            user.save()

            # Sending Signal when new User is Registered
            signals.user_registered_signal.send(sender=self.__class__, user=user, current_site=current_site)
            return user

        except Exception as e:
            message = "Something went wrong while creating user"
            raise UserRegistrationException(message=message, item={'error': e.args, 'error_tag': 'common'})

    def create_and_send_verification_link(self, current_site: str, user: User) -> None:
        encoded_user_id = encode_by_base64(str(user.id))
        verification_link = f"http://{current_site}/users/email/verification/{encoded_user_id}"

        sendgrid_email_verification_template_id = getattr(settings, "SENDGRID_VERIFY_EMAIL_TEMPLATE_KEY", None)
        username = user.first_name if user.first_name else user.email.split('@')[0]
        template_data = {
            'username': username,
            'date_time': datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S"),
            'verification_link': verification_link
        }
        sendgrid_mail(to_email=user.email, TEMPLATE_KEY=sendgrid_email_verification_template_id,
                      dynamic_data_for_template=template_data)
        return None

    def verify_user_by_verification_link(self, encoded_user_id: str) -> User:
        """
        Verification of User Email Sent with Verification Link
        """
        try:
            with transaction.atomic():
                decoded_user_id = decode_by_base64(string=encoded_user_id)
                user = self.user_services.get_user_repo().get(id=decoded_user_id)
                if not self.check_user_is_verified(email=user.email):
                    user.is_verified = True
                    user.save()
                return user
        except Exception as e:
            raise e

    # =====================================================================================
    # FORGOT PASSWORD
    # =====================================================================================
    def get_forgot_password_by_id(self, id: UUID) -> ForgotPassword:
        """
        Get Forgot Password Instance by ID
        """
        try:
            return self.forgot_password_services.get_forgot_password_repo().get(id=id)
        except Exception as e:
            raise ForgotPasswordInstanceDoesNotExist(message="Forgot password with this id is not available.",
                                                     item={'error': e.args})

    def get_forgot_password_by_user_id(self, user_id: UUID) -> ForgotPassword:
        """
        Get Forgot Password Instance by User ID
        """
        try:
            return self.forgot_password_services.get_forgot_password_repo().get(user_id=user_id)
        except Exception as e:
            raise ForgotPasswordInstanceDoesNotExist(message="Forgot password with this user_id is not available.",
                                                     item={'error': e.args})

    def get_forgot_password_by_password_token(self, token: str) -> ForgotPassword:
        """
        Get Forgot Password Instance by Password Token
        """
        try:
            return self.forgot_password_services.get_forgot_password_repo().get(password_token=token)
        except Exception as e:
            raise ForgotPasswordInstanceDoesNotExist(message="Forgot password with this token is not available.",
                                                     item={'error': e.args})

    def create_forgot_password_by_dict(self, data: dict) -> ForgotPassword:
        """
        Creates Forgot Password and Send Mail to user if Email exist
        """
        current_site = data.get('current_site')
        email = data.get('email')

        forgot_password_services = self.forgot_password_services

        email_exists = UserAppServices().check_user_email_exists(email=email)
        if not email_exists:
            raise UserDoesNotExist(message="User with this email is not exists.", item={'error_tag': 'email'})

        try:
            with transaction.atomic():
                expiry = make_aware(datetime.datetime.now() + datetime.timedelta(minutes=5))
                token = str(uuid.uuid4())
                encoded_token = encode_by_base64(str(token))

                forgot_password_url = f"http://{current_site}/reset-password-confirm/?token={encoded_token}"
                user = self.get_user_by_email(email=email)
                forgot_password_instance, created = forgot_password_services.get_forgot_password_factory().get_entity_with_get_or_create(
                    user_id=user.id, password_token=token, password_token_expiry=expiry)

                if not created:
                    forgot_password_instance.password_token = token
                    forgot_password_instance.password_token_expiry = expiry
                    forgot_password_instance.save()

                username = user.first_name if user.first_name else user.email.split('@')[0]
                template_data = {
                    'username': username,
                    'date_time': datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S"),
                    'reset_password_link': forgot_password_url
                }
                sendgrid_forgot_password_template_id = getattr(settings, "SENDGRID_FORGOT_PASSWORD_TEMPLATE_KEY", None)
                sendgrid_mail(to_email=email, TEMPLATE_KEY=sendgrid_forgot_password_template_id,
                              dynamic_data_for_template=template_data)
                return forgot_password_instance
        except Exception as e:
            raise e

    def verify_forgot_password_token(self, encoded_token: str) -> bool:
        """
        Check Forgot Password Token is Exist and is not Expired
        """
        password_token = decode_by_base64(encoded_token)
        try:
            with transaction.atomic():
                forgot_password_instance = self.get_forgot_password_by_password_token(token=password_token)
                expiration_time = forgot_password_instance.password_token_expiry
                if make_aware(datetime.datetime.now()) > expiration_time:
                    raise ForgotPasswordLinkExpired(message="Forgot Password Link is Expired.",
                                                    item={'error_tag': 'common'})
                return True
        except Exception as e:
            if isinstance(e, ForgotPasswordLinkExpired):
                raise e
            raise e

    def set_new_password_for_forgot_password(self, data: dict):
        """
        Set New Password and Remove Forgot Password Token and Expiry Time
        """
        password = data.get('password')
        current_site = data.get('current_site')
        encoded_token = data.get('encoded_token')
        password_token = decode_by_base64(encoded_token)

        if not validate_password_by_regex(password=password):
            message = "Please, Enter strong password."
            raise ValidationException(message=message, item={'error_tag': 'password'})

        try:
            with transaction.atomic():
                forgot_password_instance = self.get_forgot_password_by_password_token(token=password_token)
                # Set User's Password to new Password
                user_id = forgot_password_instance.user_id
                user = self.get_user_by_id(id=user_id)
                user.set_password(password)
                user.save()
                # After successful set new password => set None to password_token and expiry_time
                forgot_password_instance.password_token = None
                forgot_password_instance.password_token_expiry = None
                forgot_password_instance.save()
        except Exception as e:
            raise e

        try:
            username = user.first_name if user.first_name else user.email.split('@')[0]
            login_link = f"http://{current_site}/onboarding/"
            template_data = {
                'username': username,
                'date_time': datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S"),
                'login_link': login_link
            }
            sendgrid_forgot_password_completed_template_id = getattr(settings,
                                                                     "SENDGRID_FORGOT_PASSWORD_COMPLETED_TEMPLATE_KEY",
                                                                     None)
            sendgrid_mail(to_email=user.email, TEMPLATE_KEY=sendgrid_forgot_password_completed_template_id,
                          dynamic_data_for_template=template_data)
        except Exception as e:
            raise e

    # =====================================================================================
    # VISITED USER
    # =====================================================================================

    def list_visited_users(self) -> VisitedUser:
        """
        Get a list of All Visited Users
        """
        return self.visited_user_services.get_visited_user_repo().all()

    def list_visited_user_by_ip_address(self, ip_address: str) -> VisitedUser:
        """
        Get List of Visited Users by IP Address
        """
        return self.list_visited_users().filter(ip_address=ip_address)

    def check_visited_user_exists(self, email: str, ip_address: str) -> bool:
        """
        Check if Visited User is Exists
        """
        return self.list_visited_users().filter(email=email, ip_address=ip_address).exists()

    def create_visited_user(self, ip_address: str, email: str) -> VisitedUser:
        """
        Creates Visited User using email and IP Address
        """
        visited_user_services = self.visited_user_services
        try:
            visited_user_exists = self.check_visited_user_exists(email=email, ip_address=ip_address)
            if not visited_user_exists:
                visited_user = visited_user_services.get_visited_user_factory().build_entity_with_id(email=email,
                                                                                                     ip_address=ip_address)
                visited_user.save()
                return visited_user

        except Exception as e:
            message = "Something went wrong while creating visited user"
            raise VisitedUserCreationException(message=message, item={'error': e.args, 'error_tag': 'common'})

    # =====================================================================================
    # INQUIRY (CONTACT US PAGE)
    # =====================================================================================
    def get_inquiry_by_id(self, id: UUID) -> Inquiry:
        """
        Get Inquiry Instance by ID
        """
        try:
            return self.inquiry_services.get_inquiry_repo().get(id=id)
        except Exception as e:
            raise InquiryDoesNotExist(message="Inquiry is not available.",
                                                     item={'error': e.args})
    def create_inquiry_by_contact_us_form_data(self, data: dict) -> Inquiry:
        """
        Creates Inquiry by Contact Form Data
        """
        email = data.get('email')
        contact_message = data.get('contact_message')

        try:
            if email and contact_message:
                inquiry_instance = self.inquiry_services.get_inquiry_factory().build_entity_with_id(email=email,
                                                                                                    contact_message=contact_message)
                inquiry_instance.save()
                return inquiry_instance
        except Exception as e:
            raise InquiryException(message="Something went wrong while creating Inquiry.",
                                   item={'error': e.args, 'error_tag': 'common'})

    def update_inquiry_is_solved_field_by_inquiry_id(self, inquiry_id: str) -> Inquiry:
        """
        Update Inquiry is_solved Field by Inquiry ID
        """
        try:
            if inquiry_id:
                inquiry_instance = self.get_inquiry_by_id(id=uuid.UUID(inquiry_id))
                inquiry_instance.is_solved = True if not inquiry_instance.is_solved else False
                inquiry_instance.save()
                return inquiry_instance
        except Exception as e:
            raise e

from django.contrib.auth.hashers import check_password

from embermail.domain.users.models import User
from utils.django.exceptions import ValidationException, PasswordNotMatched
from utils.django.regex import validate_password_by_regex


class ProfileAppServices:

    def change_password(self, data_dict: dict) -> User:
        """
        Update User's Password
        """
        try:
            user = data_dict.get('user')
            current_password = data_dict.get('current_password')
            new_password = data_dict.get('new_password')

            if not current_password:
                error_message = "Both Password Fields are Required."
                raise ValidationException(message=error_message, item={'error_tag': 'password'})

            if not check_password(current_password, user.password):
                error_message = "Current Password Does not Matched with System."
                raise PasswordNotMatched(message=error_message, item={'error_tag': 'password'})

            if not new_password:
                error_message = "Both Password Fields are Required."
                raise ValidationException(message=error_message, item={'error_tag': 'password'})

            if not validate_password_by_regex(password=new_password):
                error_message = "At least one digit, lowercase, uppercase, special character and length should be between 8-32."
                raise ValidationException(message=error_message, item={'error_tag': 'password'})

            user.set_password(new_password)
            user.save()
            return user

        except Exception as e:
            raise e

    def update_user_profile_by_name(self, data_dict: dict) -> User:
        """
        Update User's Name
        """
        try:
            user = data_dict.get('user')
            name = data_dict.get('input_name')
            if name:
                user.first_name = name
                user.save()
                return user
            error_message = "Name Field is Required."
            raise ValidationException(message=error_message, item={'error_tag': 'name'})
        except Exception as e:
            raise e

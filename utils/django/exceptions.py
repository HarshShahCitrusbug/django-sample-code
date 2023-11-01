from dataclasses import dataclass


# =================================================================================================
# USER EXCEPTIONS
# =================================================================================================
class UserException(Exception):
    """
    Base class for User exceptions
    """
    pass


@dataclass(frozen=True)
class UserDoesNotExist(UserException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class UserDoesNotVerified(UserException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class UserAlreadyExist(UserException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class UserRegistrationException(UserException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class InvalidCredentialsException(UserException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class ValidationException(UserException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class UserLoginException(UserException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class ForgotPasswordInstanceDoesNotExist(UserException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class ForgotPasswordException(UserException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class ForgotPasswordLinkExpired(UserException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class ForgotPasswordDoesNotMatch(UserException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class VisitedUserCreationException(UserException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class InquiryException(UserException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class InquiryDoesNotExist(UserException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class SendgridEmailException(UserException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


# =================================================================================================
# CAMPAIGN EXCEPTIONS
# =================================================================================================
class CampaignException(Exception):
    """
    Base class for Campaign exceptions
    """
    pass


@dataclass(frozen=True)
class CampaignDoesNotExist(CampaignException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class CampaignAlreadyExist(CampaignException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class CampaignCreationException(CampaignException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class CampaignDataValidation(CampaignException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class ActionRequiredException(CampaignException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class CampaignTypeDoesNotExist(CampaignException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class CampaignAccessDenied(CampaignException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class CampaignReportDoesNotExist(CampaignException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class DomainListDoesNotExist(CampaignException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class DomainEmailCreationException(CampaignException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


# =================================================================================================
# PAYMENT EXCEPTIONS
# =================================================================================================
class PaymentException(Exception):
    """
    Base class for Payment exceptions
    """
    pass


@dataclass(frozen=True)
class PlanDoesNotExist(PaymentException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class PaymentDoesNotExist(PaymentException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class ValidPaymentData(PaymentException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class PaymentMethodDoesNotExist(PaymentException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class PaymentMethodCreationException(PaymentException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class StripePaymentMethodException(PaymentException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class StripeSubscriptionException(PaymentException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class StripeCustomerException(PaymentException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


# =================================================================================================
# TEMPLATE-THREAD EXCEPTIONS
# =================================================================================================
class TemplateException(Exception):
    """
    Base class for Template-Thread exceptions
    """
    pass


@dataclass(frozen=True)
class TemplateDoesNotExist(TemplateException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class TemplateAlreadyExist(TemplateException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class TemplateThreadAccessDenied(TemplateException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


@dataclass(frozen=True)
class ThreadDoesNotExist(TemplateException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)


# =================================================================================================
# PROFILE EXCEPTION
# =================================================================================================

class ProfileException(Exception):
    """
    Base class for Template-Thread exceptions
    """
    pass


@dataclass(frozen=True)
class PasswordNotMatched(ProfileException):
    message: str
    item: dict

    def __str__(self):
        return "{}: {}".format(self.message, self.item)

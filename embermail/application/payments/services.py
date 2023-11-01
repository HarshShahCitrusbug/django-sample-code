import uuid
from datetime import datetime

import stripe
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.db.models.query import QuerySet

from embermail.domain.users.models import User
from embermail.domain.campaigns.models import CampaignData
from embermail.application.users.services import UserAppServices
from embermail.domain.campaigns.services import CampaignServices
from embermail.domain.text_choices import PaymentStatusChoices, CampaignActionRequiredChoices
from embermail.application.campaigns.services import CampaignAppServices
from embermail.domain.payments.models import Plan, PaymentMethod, Payment, PaymentData
from embermail.domain.payments.services import PlanServices, PaymentMethodServices, PaymentServices
from utils.data_manipulation.type_conversion import encode_by_base64
from utils.django.exceptions import PaymentMethodCreationException, PlanDoesNotExist, PaymentMethodDoesNotExist, \
    StripeCustomerException, StripePaymentMethodException, StripeSubscriptionException, UserDoesNotExist, \
    PaymentDoesNotExist, ValidPaymentData


class PaymentAppServices:
    plan_services = PlanServices()
    payment_services = PaymentServices()
    payment_method_services = PaymentMethodServices()

    # =====================================================================================
    # PLAN
    # =====================================================================================
    def get_plan_by_id(self, id: UUID) -> Plan:
        """
        Get plan instance by id
        """
        try:
            return self.plan_services.get_plan_repo().get(id=id)
        except Exception as e:
            raise PlanDoesNotExist(message="Plan not Found.", item={'error': e.args})

    def get_plan_by_name(self, name: str) -> Plan:
        """
        Get plan instance by name
        """
        try:
            return self.plan_services.get_plan_repo().get(name=name)
        except Exception as e:
            raise PlanDoesNotExist(message="Plan not Found.", item={'error': e.args})

    def list_plans(self) -> QuerySet[Plan]:
        """
        List all plans
        """
        return self.plan_services.get_plan_repo().all()

    def get_stripe_price_id_by_plan_id(self, plan_id: str) -> str:
        """
        Get Stripe Price ID by Plan ID
        """
        try:
            with transaction.atomic():
                plan = self.get_plan_by_id(id=uuid.UUID(plan_id))
                stripe_price_id = plan.stripe_price_id
                return stripe_price_id
        except Exception as e:
            raise e  # PlanDoesNotExist(message="Plan not Found.", item={'error_tag': 'common', 'error': e.args})

    # =====================================================================================
    # PAYMENT
    # =====================================================================================

    def get_payment_by_id(self, id: UUID) -> Payment:
        """
        Get payment instance by id
        """
        try:
            return self.payment_services.get_payment_repo().get(id=id)
        except Exception as e:
            raise PaymentDoesNotExist(message="Payment not Found.", item={'error': e.args})

    def get_latest_payment_by_warmup_email(self, warmup_email: str) -> Payment:
        """
        Get payment instance by warmup_email
        """
        try:
            payment = self.list_payments().filter(warmup_email=warmup_email).order_by('-created_at')[0]
            return payment
        except Exception as e:
            raise PaymentDoesNotExist(message="Payment not Found.", item={'error': e.args})

    def list_payments(self) -> QuerySet[Payment]:
        """
        List all payments
        """
        return self.payment_services.get_payment_repo().all()

    def list_payments_by_master_user_id(self, master_user_id: uuid) -> QuerySet[Payment]:
        """
        List All Payment History by Master User
        """
        return self.list_payments().filter(master_user_id=master_user_id)

    # =====================================================================================
    # PAYMENT METHOD
    # =====================================================================================
    def list_all_payment_methods(self) -> QuerySet[PaymentMethod]:
        """
        List All Payment Methods
        """
        return self.payment_method_services.get_payment_method_repo().all()

    def list_payment_methods_by_master_user_id(self, master_user_id: uuid.UUID) -> QuerySet[PaymentMethod]:
        """
        List Payment Methods Linked With Master User and Passed CVC
        """
        payment_methods = self.list_all_payment_methods().filter(user_id=master_user_id,
                                                                 stripe_payment_method__card__checks__cvc_check='pass')
        return payment_methods

    def get_payment_method_by_user_id_and_entered_card_data(self, user_id: uuid,
                                                            stripe_payment_method: dict) -> PaymentMethod:
        """
        Get Payment Method Instance by UserID and Entered Card Payment Method Object Data
        """
        try:
            entered_card_detail_dict = stripe_payment_method.get("card")
            if entered_card_detail_dict:
                entered_card_last4 = entered_card_detail_dict.get("last4")
                entered_card_brand = entered_card_detail_dict.get("brand")
                entered_exp_month = entered_card_detail_dict.get("exp_month")
                entered_exp_year = entered_card_detail_dict.get("exp_year")

                payment_method = self.payment_method_services.get_payment_method_repo().get(
                    user_id=user_id,
                    stripe_payment_method__card__exp_month=entered_exp_month,
                    stripe_payment_method__card__exp_year=entered_exp_year,
                    stripe_payment_method__card__brand=entered_card_brand,
                    stripe_payment_method__card__last4=entered_card_last4)
                return payment_method
            raise PaymentMethodDoesNotExist(message="Payment Method Doesn't Exist.", item={})
        except Exception as e:
            raise e

    def get_cleaned_data_from_entered_card(self, entered_card_dict: dict) -> dict:
        """
        Cleaning Card Data
        """
        card_dict = dict()
        card_dict['card_number'] = entered_card_dict.get('card_number').replace(" ", "")
        card_dict['card_holder'] = entered_card_dict.get('card_holder_name')
        card_dict['cvc'] = entered_card_dict.get('card_cvc')
        card_expiry_list = entered_card_dict.get('card_expiry').replace(" ", "").split('/')
        card_dict['exp_month'] = card_expiry_list[0]
        card_dict['exp_year'] = card_expiry_list[1]
        card_dict['full_name'] = entered_card_dict.get('full_name')
        card_dict['city'] = entered_card_dict.get('city')
        card_dict['zip'] = entered_card_dict.get('zip')
        card_dict['country'] = entered_card_dict.get('country')
        card_dict['email'] = entered_card_dict.get('email')

        return card_dict

    def check_payment_card_exist(self, user_id: uuid.UUID, stripe_payment_method: dict) -> bool:
        """
        Check Entered Card Details is Exist in Payment Method DB
        """
        entered_card_detail_dict = stripe_payment_method.get("card")
        if entered_card_detail_dict:
            entered_card_last4 = entered_card_detail_dict.get("last4")
            entered_card_brand = entered_card_detail_dict.get("brand")
            entered_exp_month = entered_card_detail_dict.get("exp_month")
            entered_exp_year = entered_card_detail_dict.get("exp_year")

        payment_method_exist = self.payment_method_services.get_payment_method_repo().filter(user_id=user_id,
                                                                                             stripe_payment_method__card__exp_month=entered_exp_month,
                                                                                             stripe_payment_method__card__brand=entered_card_brand,
                                                                                             stripe_payment_method__card__exp_year=entered_exp_year,
                                                                                             stripe_payment_method__card__last4=entered_card_last4).exists()
        return payment_method_exist

    def create_payment_method(self, user_id, stripe_payment_method_object: dict) -> PaymentMethod:
        """
        Create Payment Method Instance
        """
        try:
            payment_method_instance = self.payment_method_services.get_payment_method_factory().build_entity_with_id(
                user_id=user_id, stripe_payment_method=stripe_payment_method_object)
            payment_method_instance.save()
            return payment_method_instance
        except Exception as e:
            raise PaymentMethodCreationException(message="Something Went Wrong While Creating Payment Method Instance.",
                                                 item={'error': e.args})

    def get_payment_method(self, user: User, stripe_payment_method: dict) -> PaymentMethod:
        """
        Get or Create Payment Method Instance
        """
        try:
            is_payment_method_exist = self.check_payment_card_exist(user_id=user.id,
                                                                    stripe_payment_method=stripe_payment_method)
            if is_payment_method_exist:
                # Get Payment Method Instance
                payment_method_instance = self.get_payment_method_by_user_id_and_entered_card_data(user_id=user.id,
                                                                                                   stripe_payment_method=stripe_payment_method)
            else:
                # Create PaymentMethod Instance
                payment_method_instance = self.create_payment_method(user_id=user.id,
                                                                     stripe_payment_method_object=stripe_payment_method)
            return payment_method_instance
        except Exception as e:
            # Raise PaymentMethodDoesNotExist and PaymentMethodCreationException
            raise e

    def create_payment_and_subscribe(self, user: User, plan_id: str, stripe_payment_method_id: str,
                                     warmup_email: str, selected_flow: str, email_provider: str) -> bool:
        """
        Create Subscription using Entered Card Details, Payment Method id and Customer id
        """
        try:
            subscription = None
            with transaction.atomic():
                # Retrieve Stripe Payment Method Object by PaymentMethodID
                stripe_payment_method = StripeAppServices().retrieve_stripe_payment_method(stripe_payment_method_id)

                # Get Stripe Payment Method ID if Created
                payment_method_instance = PaymentAppServices().get_payment_method(user=user,
                                                                                  stripe_payment_method=stripe_payment_method)
                stripe_payment_method_id = payment_method_instance.stripe_payment_method.get('id')

                # Get Stripe Customer ID
                stripe_customer_id = UserAppServices().get_or_create_stripe_customer_id(user=user)

                # Attach Stripe Payment Method to Stripe Customer
                StripeAppServices().attach_stripe_payment_method_to_stripe_customer(
                    stripe_payment_method_id=stripe_payment_method_id, stripe_customer_id=stripe_customer_id)

                # Get Stripe Price ID by Selected Plan ID
                stripe_price_id = self.get_stripe_price_id_by_plan_id(plan_id=plan_id)

                # Create Subscription
                subscription = StripeAppServices().create_stripe_subscription(stripe_customer_id=stripe_customer_id,
                                                                              stripe_price_id=stripe_price_id,
                                                                              default_payment_method_id=stripe_payment_method_id,
                                                                              master_user_id=str(user.id),
                                                                              warmup_email=warmup_email)
            if subscription:
                with transaction.atomic():
                    # Getting Invoice Download URL and Invoice Name from Stripe
                    invoice_data_dict = StripeAppServices().get_stripe_invoice_download_url_and_name(
                        stripe_invoice_id=subscription.get('latest_invoice'))
                    invoice_download_url = invoice_data_dict.get('invoice_download_url') if invoice_data_dict.get(
                        'invoice_download_url') else ""
                    invoice_name = "Invoice-" + invoice_data_dict.get('invoice_name') if invoice_data_dict.get(
                        'invoice_name') else ""

                    # Deciding Payment Status
                    payment_status = PaymentStatusChoices.INCOMPLETE
                    if subscription.get('status') == "active":
                        payment_status = PaymentStatusChoices.SUCCESS
                    if subscription.get('status') == "pending":
                        payment_status = PaymentStatusChoices.PENDING

                    # Create Payment History
                    # payment_data = PaymentData(warmup_email=warmup_email, master_user_id=user.id,
                    #                            purchased_plan_id=uuid.UUID(plan_id),
                    #                            stripe_subscription=subscription,
                    #                            payment_status=payment_status,
                    #                            invoice_download_url=invoice_download_url,
                    #                            invoice_name=invoice_name)
                    # payment_instance = self.payment_services.get_payment_factory().build_entity_with_id(
                    #     payment_data=payment_data)
                    # payment_instance.save()

                    if payment_status == PaymentStatusChoices.SUCCESS:
                        if selected_flow == 'inbox' or selected_flow == 'make_payment':
                            # Updating Campaigns Plan ID , Next Invoice Date and Action Required Field for Inbox Flow
                            campaign_instance = CampaignAppServices().get_campaign_by_email(email=warmup_email)
                            campaign_instance.plan_id = plan_id
                            next_invoice_in_timestamp = subscription.get("current_period_end")
                            campaign_instance.next_invoice_date = datetime.fromtimestamp(
                                next_invoice_in_timestamp).date()
                            campaign_instance.action_required = CampaignActionRequiredChoices.NONE
                        else:
                            # Creating Campaign for Invite flow
                            next_invoice_in_timestamp = subscription.get("current_period_end")
                            campaign_data = CampaignData(email=warmup_email, email_service_provider=email_provider,
                                                         master_user_id=user.id, plan_id=uuid.UUID(plan_id),
                                                         next_invoice_date=datetime.fromtimestamp(
                                                             next_invoice_in_timestamp).date(),
                                                         action_required=CampaignActionRequiredChoices.APP_PASSWORD_REQUIRED)

                            campaign_instance = CampaignServices().get_campaign_factory().build_entity_with_id(
                                campaign_data=campaign_data)
                        campaign_instance.save()
                        # Update Payment Method Instance On Successful Payment if payment method is not updated
                        if not payment_method_instance.stripe_payment_method.get("card").get("checks").get(
                                "cvc_check") == 'pass':
                            updated_stripe_payment_method_object = StripeAppServices().retrieve_stripe_payment_method(
                                payment_method_id=stripe_payment_method_id)
                            payment_method_instance.stripe_payment_method = updated_stripe_payment_method_object
                            payment_method_instance.save()
                        return True
                    else:
                        raise ValidPaymentData(message="Enter proper billing details.", item={'error_tag': 'common'})
        except Exception as e:
            raise e

    def create_payment_and_update_campaign_on_successful_recurring_payment(self, subscription: dict) -> bool:
        """
        Creating Payment for Recurring on Successful Payment
        Updating Campaign by next_invoice_date and action_required
        """
        try:
            with transaction.atomic():
                # Getting Data from Stripe Subscription Object
                # stripe_price_id = subscription.get('plan').get('id') # TODO: Future Use
                # Getting Invoice Download URL and Invoice Name from Stripe
                invoice_data_dict = StripeAppServices().get_stripe_invoice_download_url_and_name(
                    stripe_invoice_id=subscription.get('latest_invoice'))
                invoice_download_url = invoice_data_dict.get('invoice_download_url') if invoice_data_dict.get(
                    'invoice_download_url') else ""
                invoice_name = "Invoice-" + invoice_data_dict.get('invoice_name') if invoice_data_dict.get(
                    'invoice_name') else ""

                # Deciding Payment Status
                payment_status = PaymentStatusChoices.INCOMPLETE
                if subscription.get('status') == "active":
                    payment_status = PaymentStatusChoices.SUCCESS
                if subscription.get('status') == "pending":
                    payment_status = PaymentStatusChoices.PENDING

                # Get Campaign Instance by Warmup Email
                warmup_email = subscription.get('metadata').get('warmup_email')
                master_user_id = subscription.get('metadata').get('master_user_id')
                campaign_instance = CampaignAppServices().get_campaign_by_email(email=warmup_email)

                # Create Payment History
                payment_data = PaymentData(warmup_email=warmup_email, master_user_id=uuid.UUID(master_user_id),
                                           purchased_plan_id=campaign_instance.plan_id,
                                           stripe_subscription=subscription,
                                           payment_status=payment_status,
                                           invoice_download_url=invoice_download_url,
                                           invoice_name=invoice_name)
                payment_instance = self.payment_services.get_payment_factory().build_entity_with_id(
                    payment_data=payment_data)
                payment_instance.save()

                if payment_status == PaymentStatusChoices.SUCCESS:
                    # Updating Next Invoice Date and Action Required Field of Campaign
                    next_invoice_in_timestamp = subscription.get("current_period_end")
                    campaign_instance.next_invoice_date = datetime.fromtimestamp(next_invoice_in_timestamp).date()
                    campaign_instance.action_required = CampaignActionRequiredChoices.NONE
                    campaign_instance.save()
        except Exception as e:
            # TODO : Send mail for error related
            raise e

    def create_payment_and_update_campaign_on_failed_recurring_payment(self, subscription: dict) -> bool:
        """
        Creating Payment History for Recurring on UnSuccessful Payment
        Updating Campaign by is_stopped,
        """
        try:
            with transaction.atomic():
                # Getting Invoice Download URL and Invoice Name from Stripe
                invoice_data_dict = StripeAppServices().get_stripe_invoice_download_url_and_name(
                    stripe_invoice_id=subscription.get('latest_invoice'))
                invoice_download_url = invoice_data_dict.get('invoice_download_url') if invoice_data_dict.get(
                    'invoice_download_url') else ""
                invoice_name = "Invoice-" + invoice_data_dict.get('invoice_name') if invoice_data_dict.get(
                    'invoice_name') else ""

                # Get Campaign Instance by Warmup Email
                warmup_email = subscription.get('metadata').get('warmup_email')
                master_user_id = subscription.get('metadata').get('master_user_id')
                campaign_instance = CampaignAppServices().get_campaign_by_email(email=warmup_email)

                # Create Payment History
                payment_data = PaymentData(warmup_email=warmup_email, master_user_id=uuid.UUID(master_user_id),
                                           purchased_plan_id=campaign_instance.plan_id,
                                           stripe_subscription=subscription,
                                           payment_status=PaymentStatusChoices.INCOMPLETE,
                                           invoice_download_url=invoice_download_url,
                                           invoice_name=invoice_name)
                payment_instance = self.payment_services.get_payment_factory().build_entity_with_id(
                    payment_data=payment_data)
                payment_instance.save()

                # Updating Next Invoice Date, Action Required, plan_id and is_stopped Field of Campaign
                campaign_instance.next_invoice_date = None
                campaign_instance.action_required = CampaignActionRequiredChoices.PAYMENT_REQUIRED
                campaign_instance.plan_id = None
                campaign_instance.is_stopped = True
                campaign_instance.save()

        except Exception as e:
            # TODO : Send mail for error related
            raise e


class StripeAppServices:
    def __init__(self):
        stripe.api_key = settings.STRIPE_API_KEY

    def create_stripe_customer(self, email: str, user_id: str) -> stripe.Customer:
        """
        Creates Stripe Customer
        """
        try:
            stripe_customer = stripe.Customer.create(email=email, metadata={'user_id': user_id})
            return stripe_customer

        except stripe.error.InvalidRequestError as e:
            raise StripeCustomerException(message="Invalid Request to Stripe.",
                                          item={'error': e.error, 'error_tag': 'customer'})
        except stripe.error.APIConnectionError as e:
            raise StripeCustomerException(message="API Connection Error.",
                                          item={'error': e.error, 'error_tag': 'customer'})
        except stripe.error.AuthenticationError as e:
            raise StripeCustomerException(message="Authentication Failed.",
                                          item={'error': e.error, 'error_tag': 'customer'})
        except stripe.error.PermissionError as e:
            raise StripeCustomerException(message="Permissions Denied.",
                                          item={'error': e.error, 'error_tag': 'customer'})
        except stripe.error.RateLimitError as e:
            raise StripeCustomerException(message="API Call Limit.", item={'error': e.error, 'error_tag': 'customer'})
        except Exception as e:
            raise e

    def create_stripe_payment_method(self, card_dict: dict) -> stripe.PaymentMethod:
        """
        Create Stripe Payment Method
        """
        try:
            # Getting Data from Entered Card
            card_number = card_dict.get("card_number")
            exp_month = card_dict.get("exp_month")
            exp_year = card_dict.get("exp_year")
            cvc = card_dict.get("cvc")
            full_name = card_dict.get('full_name')
            city = card_dict.get('city')
            postal_code = card_dict.get('zip')
            country = card_dict.get('country')
            email = card_dict.get('email')

            payment_method = stripe.PaymentMethod.create(
                type="card",
                card={
                    "number": card_number,
                    "exp_month": exp_month,
                    "exp_year": exp_year,
                    "cvc": cvc,
                },
                billing_details={
                    'email': email,
                    'name': full_name,
                    'address': {
                        'line1': f"{city}, {country} - {postal_code}",
                        'city': city,
                        'country': country,
                        'postal_code': postal_code,
                    }
                }
            )
            return payment_method

        except stripe.error.CardError as e:
            raise StripePaymentMethodException(message="Payment Error.",
                                               item={'error': e.error, 'error_tag': 'payment_method'})
        except stripe.error.InvalidRequestError as e:
            raise StripePaymentMethodException(message="Invalid Request to Stripe.",
                                               item={'error': e.error, 'error_tag': 'payment_method'})
        except stripe.error.APIConnectionError as e:
            raise StripePaymentMethodException(message="API Connection Error.",
                                               item={'error': e.error, 'error_tag': 'payment_method'})
        except stripe.error.AuthenticationError as e:
            raise StripePaymentMethodException(message="Authentication Failed.",
                                               item={'error': e.error, 'error_tag': 'payment_method'})
        except stripe.error.PermissionError as e:
            raise StripePaymentMethodException(message="Permissions Denied.",
                                               item={'error': e.error, 'error_tag': 'payment_method'})
        except stripe.error.RateLimitError as e:
            raise StripePaymentMethodException(message="API Call Limit.",
                                               item={'error': e.error, 'error_tag': 'payment_method'})
        except Exception as e:
            raise StripePaymentMethodException(message="Error While Creating Stripe Payment Method.",
                                               item={'error': e.error, 'error_tag': 'payment_method'})

    def retrieve_stripe_payment_method(self, payment_method_id: str) -> stripe.PaymentMethod:
        """
        Retrieve Updated Stripe Payment Method
        """
        try:
            stripe_payment_method_object = stripe.PaymentMethod.retrieve(id=payment_method_id)
            return stripe_payment_method_object

        except stripe.error.InvalidRequestError as e:
            raise StripePaymentMethodException(message="Invalid Request to Stripe.",
                                               item={'error': e.error, 'error_tag': 'retrive_payment_method'})
        except stripe.error.APIConnectionError as e:
            raise StripePaymentMethodException(message="API Connection Error.",
                                               item={'error': e.error, 'error_tag': 'retrive_payment_method'})
        except stripe.error.AuthenticationError as e:
            raise StripePaymentMethodException(message="Authentication Failed.",
                                               item={'error': e.error, 'error_tag': 'retrive_payment_method'})
        except stripe.error.PermissionError as e:
            raise StripePaymentMethodException(message="Permissions Denied.",
                                               item={'error': e.error, 'error_tag': 'retrive_payment_method'})
        except stripe.error.RateLimitError as e:
            raise StripePaymentMethodException(message="API Call Limit.",
                                               item={'error': e.error, 'error_tag': 'retrive_payment_method'})
        except Exception as e:
            raise e

    def get_stripe_payment_method_id(self, user: User, entered_card_dict: dict) -> str:
        """
        Returns Stripe's Payment Method ID for Entered Card
        """
        payment_method_instance = PaymentAppServices().get_payment_method(user=user,
                                                                          entered_card_dict=entered_card_dict)

        stripe_payment_method_id = payment_method_instance.stripe_payment_method['id']
        return stripe_payment_method_id

    def create_stripe_subscription(self, stripe_customer_id: str, stripe_price_id: str, default_payment_method_id: str,
                                   master_user_id: str, warmup_email: str) -> stripe.Subscription:
        """
        Create Recurring Subscription
        """
        try:
            subscription = stripe.Subscription.create(customer=stripe_customer_id,
                                                      items=[{"price": f"{stripe_price_id}"}],
                                                      description="Embermail Email Warmup Services",
                                                      collection_method="charge_automatically",
                                                      default_payment_method=default_payment_method_id,
                                                      payment_settings={
                                                          "save_default_payment_method": "on_subscription",
                                                          "payment_method_options": {"card": {
                                                              "request_three_d_secure": "automatic", }}},
                                                      off_session=True,
                                                      metadata={
                                                          "master_user_id": master_user_id,
                                                          "warmup_email": warmup_email,
                                                      })
            return subscription

        except stripe.error.CardError as e:
            raise StripeSubscriptionException(message="Payment Error.",
                                              item={'error': e.error, 'error_tag': 'subscription'})
        except stripe.error.InvalidRequestError as e:
            raise StripeSubscriptionException(message="Invalid Request to Stripe.",
                                              item={'error': e.error, 'error_tag': 'subscription'})
        except stripe.error.APIConnectionError as e:
            raise StripeSubscriptionException(message="API Connection Error.",
                                              item={'error': e.error, 'error_tag': 'subscription'})
        except stripe.error.AuthenticationError as e:
            raise StripeSubscriptionException(message="Authentication Failed.",
                                              item={'error': e.error, 'error_tag': 'subscription'})
        except stripe.error.PermissionError as e:
            raise StripeSubscriptionException(message="Permissions Denied.",
                                              item={'error': e.error, 'error_tag': 'subscription'})
        except stripe.error.RateLimitError as e:
            raise StripeSubscriptionException(message="API Call Limit.",
                                              item={'error': e.error, 'error_tag': 'subscription'})
        except Exception as e:
            raise e

    def attach_stripe_payment_method_to_stripe_customer(self, stripe_payment_method_id: str,
                                                        stripe_customer_id: str) -> None:
        try:
            stripe.PaymentMethod.attach(stripe_payment_method_id, customer=stripe_customer_id)
            return None

        except stripe.error.InvalidRequestError as e:
            raise StripePaymentMethodException(message="Invalid Request to Stripe.",
                                               item={'error': e.error, 'error_tag': 'payment_method_attach'})
        except stripe.error.APIConnectionError as e:
            raise StripePaymentMethodException(message="API Connection Error.",
                                               item={'error': e.error, 'error_tag': 'payment_method_attach'})
        except stripe.error.AuthenticationError as e:
            raise StripePaymentMethodException(message="Authentication Failed.",
                                               item={'error': e.error, 'error_tag': 'payment_method_attach'})
        except stripe.error.PermissionError as e:
            raise StripePaymentMethodException(message="Permissions Denied.",
                                               item={'error': e.error, 'error_tag': 'payment_method_attach'})
        except stripe.error.RateLimitError as e:
            raise StripePaymentMethodException(message="API Call Limit.",
                                               item={'error': e.error, 'error_tag': 'payment_method_attach'})
        except Exception as e:
            raise e

    def get_stripe_invoice_download_url_and_name(self, stripe_invoice_id: str) -> dict:
        try:
            invoice_data_dict = dict()
            stripe_invoice_object = stripe.Invoice.retrieve(stripe_invoice_id)
            invoice_data_dict['invoice_name'] = stripe_invoice_object.get('number')
            # Setting invoice_download_url as Receipt PDF URL
            stripe_charge_id = stripe_invoice_object.get('charge')
            if stripe_charge_id:
                stripe_charge_object = stripe.Charge.retrieve(stripe_charge_id)
                receipt_url = stripe_charge_object.get('receipt_url')
                insert_position = receipt_url.index("?s=ap")
                modified_receipt_url = receipt_url[:insert_position] + "/pdf" + receipt_url[insert_position:]
                invoice_data_dict['invoice_download_url'] = modified_receipt_url

            return invoice_data_dict

        except stripe.error.InvalidRequestError as e:
            raise StripePaymentMethodException(message="Invalid Request to Stripe.",
                                               item={'error': e.error, 'error_tag': 'invoice_charge_data'})
        except stripe.error.APIConnectionError as e:
            raise StripePaymentMethodException(message="API Connection Error.",
                                               item={'error': e.error, 'error_tag': 'invoice_charge_data'})
        except stripe.error.AuthenticationError as e:
            raise StripePaymentMethodException(message="Authentication Failed.",
                                               item={'error': e.error, 'error_tag': 'invoice_charge_data'})
        except stripe.error.PermissionError as e:
            raise StripePaymentMethodException(message="Permissions Denied.",
                                               item={'error': e.error, 'error_tag': 'invoice_charge_data'})
        except stripe.error.RateLimitError as e:
            raise StripePaymentMethodException(message="API Call Limit.",
                                               item={'error': e.error, 'error_tag': 'invoice_charge_data'})
        except Exception as e:
            raise e

    def cancel_subscription_by_stripe_subscription_id(self, subscription_id: str) -> stripe.Subscription:
        """
        Cancel a Subscription at period end by subscription ID
        """
        try:
            canceled_subscription = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
            return canceled_subscription
        except stripe.error.InvalidRequestError as e:
            raise StripeSubscriptionException(message="Invalid Request to Stripe.",
                                              item={'error': e.error, 'error_tag': 'cancel_subscription'})
        except stripe.error.APIConnectionError as e:
            raise StripeSubscriptionException(message="API Connection Error.",
                                              item={'error': e.error, 'error_tag': 'cancel_subscription'})
        except stripe.error.AuthenticationError as e:
            raise StripeSubscriptionException(message="Authentication Failed.",
                                              item={'error': e.error, 'error_tag': 'cancel_subscription'})
        except stripe.error.PermissionError as e:
            raise StripeSubscriptionException(message="Permissions Denied.",
                                              item={'error': e.error, 'error_tag': 'cancel_subscription'})
        except stripe.error.RateLimitError as e:
            raise StripeSubscriptionException(message="API Call Limit.",
                                              item={'error': e.error, 'error_tag': 'cancel_subscription'})
        except Exception as e:
            raise e

import json
import uuid

import stripe
from django.views import View
from django.conf import settings
from django.shortcuts import render
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin

from embermail.application.campaigns.services import CampaignAppServices
from embermail.application.payments.services import PaymentAppServices
from utils.django.exceptions import PaymentMethodCreationException, PaymentMethodDoesNotExist, PlanDoesNotExist, \
    StripeCustomerException, \
    StripePaymentMethodException, StripeSubscriptionException, UserDoesNotExist, ValidationException, \
    CampaignAlreadyExist, InvalidCredentialsException, CampaignCreationException, ValidPaymentData, \
    CampaignDoesNotExist, CampaignAccessDenied


class PlanSelectionView(LoginRequiredMixin, View):
    """
    View for Displaying Plans
    """

    def get(self, request):
        """
        Render Plan Selection Page to Display Plan List
        """
        try:
            campaign_id = request.GET.get('campaign')
            if campaign_id:
                campaign_instance = CampaignAppServices().get_campaign_by_id(id=uuid.UUID(campaign_id))
                if not campaign_instance.master_user_id == request.user.id:
                    raise CampaignAccessDenied(message="Access Denied.", item={'redirect': "campaign_list"})
                if campaign_instance:
                    request.session['warmup_email_address'] = campaign_instance.email
                    request.session['selected_flow'] = "make_payment"
            plan_list = list(
                PaymentAppServices().list_plans().filter(is_active=True).order_by("plan_duration").values())
            context = {
                'plans': plan_list,
            }
            return render(request, 'payment/plan_selection.html', context=context)
        except CampaignAccessDenied as cad:
            messages.error(message=cad.message)
            redirect = cad.item.get('redirect')
            if redirect == "campaign_list":
                return redirect("campaigns:list")
        except Exception as e:
            return render(request, '404.html')  # TODO : Return 404 Error Page


class CompletePaymentView(LoginRequiredMixin, View):
    """
    View for Payment Page and Create Subscription
    """

    def get(self, request):
        """
        Render Card Payment with selected Plan Details and Displaying Existing Payment Methods
        """
        plan_id = request.GET.get('plan')
        try:
            # Get Plan Details
            plan = PaymentAppServices().get_plan_by_id(id=plan_id)
            request.session['selected_plan_id'] = plan_id

            # List Existing Payment Methods
            # TODO: Add Payment Method List in Html
            # payment_methods_list = list(PaymentAppServices().list_payment_methods_by_master_user_id(
            #     master_user_id=request.user.id).values('stripe_payment_method__id',
            #                                            'stripe_payment_method__card__brand',
            #                                            'stripe_payment_method__card__last4',
            #                                            'stripe_payment_method__card__checks__cvc_check',
            #                                            'stripe_payment_method__card__exp_year',
            #                                            'stripe_payment_method__card__exp_month'))

            country_list = getattr(settings, "COUNTRY_ISO_CODES_LIST", None)
            context = {
                'plan': plan,
                'country_list': country_list,
                'email': request.session.get('warmup_email_address'),
                # 'payment_methods': payment_methods_list, # TODO : Future Use
            }
            return render(request, 'payment/complete_payment.html', context=context)
        except Exception as e:
            print(e)
            return render(request, '404.html')  # TODO : Return 404 Error Page

    def post(self, request):
        """
        Get or Create Payment Method using Card Details
        Get or Create Stripe Customer ID
        Create Subscription
        Create Campaign for Invite Flow
        """
        if 'warmup_email_address' not in request.session or 'selected_plan_id' not in request.session:
            messages.warning(request, "Something went Wrong. Please Configure Again.")
            return JsonResponse({'redirect': 'home'})

        # get Email and selected_flow for referencing Payment and Campaign from Session
        warmup_email = request.session.get('warmup_email_address')
        selected_flow = request.session.get('selected_flow')
        email_provider = request.session.get('email_provider')

        # AJAX post Method
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            try:
                ajax_data_dict = json.load(request)
                stripe_payment_method_id = ajax_data_dict.get('stripe_payment_method_id')
                plan_id = request.session.get('selected_plan_id')

                payment_status = PaymentAppServices().create_payment_and_subscribe(user=request.user, plan_id=plan_id,
                                                                                   stripe_payment_method_id=stripe_payment_method_id,
                                                                                   warmup_email=warmup_email,
                                                                                   selected_flow=selected_flow,
                                                                                   email_provider=email_provider)
                if payment_status:
                    if 'selected_plan_id' in request.session:
                        del request.session['selected_plan_id']
                    return JsonResponse({'payment_status': True})
                message = "Something went wrong while Completing Payment and Subscription."
                messages.error(request, message)
                return JsonResponse({'error_message': message})
            except PaymentMethodDoesNotExist as pmdne:
                messages.error(request, pmdne.message)
                return JsonResponse({'error_message': pmdne.message, 'error': pmdne.item.get('error'),
                                     'error_tag': pmdne.item.get('error_tag')})
            except ValidPaymentData as vpd:
                messages.error(request, vpd.message)
                return JsonResponse({'error_message': vpd.message, 'error': vpd.item.get('error'),
                                     'error_tag': vpd.item.get('error_tag')})
            except StripePaymentMethodException as spme:
                messages.error(request, spme.item.get('error').get('message'))
                return JsonResponse({'error_message': spme.message, 'error': spme.item.get('error'),
                                     'error_tag': spme.item.get('error_tag')})
            except PaymentMethodCreationException as pmce:
                messages.error(request, pmce.message)
                return JsonResponse({'error_message': pmce.message, 'error': pmce.item.get('error'),
                                     'error_tag': pmce.item.get('error_tag')})
            except StripeCustomerException as sce:
                messages.error(request, sce.item.get('error').get('message'))
                return JsonResponse({'error_message': sce.message, 'error': sce.item.get('error'),
                                     'error_tag': sce.item.get('error_tag')})
            except PlanDoesNotExist as pdne:
                messages.error(request, pdne.message)
                return JsonResponse({'error_message': pdne.message, 'error': pdne.item.get('error'),
                                     'error_tag': 'common'})
            except StripeSubscriptionException as sse:
                messages.error(request, sse.item.get('error').get('message'))
                return JsonResponse({'error_message': sse.message, 'error': sse.item.get('error'),
                                     'error_tag': sse.item.get('error_tag')})
            except CampaignDoesNotExist as cdne:
                messages.error(request, cdne.message)
                return JsonResponse({'error_message': cdne.message, 'error_tag': cdne.item.get('error_tag'),
                                     'error': cdne.item.get('error')})
            except Exception as e:
                # TODO : Redirect to 404 page using js
                return JsonResponse({'error_message': "Something went wrong while doing payment.", 'error': e.args[0]})


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Stripe Webhook Events Handler
    """
    stripe.api_key = settings.STRIPE_API_KEY
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    payload = request.body
    event = None

    sig_header = request.headers["STRIPE_SIGNATURE"]

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=webhook_secret
        )
    except ValueError as e:
        return HttpResponse(status=400)

    # Handle the event
    if event["type"] == "account.updated":
        account = event["data"]["object"]
    elif event["type"] == "account.external_account.created":
        external_account = event["data"]["object"]
    elif event["type"] == "account.external_account.deleted":
        external_account = event["data"]["object"]
    elif event["type"] == "account.external_account.updated":
        external_account = event["data"]["object"]
    elif event["type"] == "balance.available":
        balance = event["data"]["object"]
    elif event["type"] == "billing_portal.configuration.created":
        configuration = event["data"]["object"]
    elif event["type"] == "billing_portal.configuration.updated":
        configuration = event["data"]["object"]
    elif event["type"] == "billing_portal.session.created":
        session = event["data"]["object"]
    elif event["type"] == "capability.updated":
        capability = event["data"]["object"]
    elif event["type"] == "cash_balance.funds_available":
        cash_balance = event["data"]["object"]
    elif event["type"] == "charge.captured":
        charge = event["data"]["object"]
    elif event["type"] == "charge.expired":
        charge = event["data"]["object"]
    elif event["type"] == "charge.failed":
        charge = event["data"]["object"]
    elif event["type"] == "charge.pending":
        charge = event["data"]["object"]
    elif event["type"] == "charge.refunded":
        charge = event["data"]["object"]
    elif event["type"] == "charge.succeeded":
        charge = event["data"]["object"]
    elif event["type"] == "charge.updated":
        charge = event["data"]["object"]
    elif event["type"] == "charge.dispute.closed":
        dispute = event["data"]["object"]
    elif event["type"] == "charge.dispute.created":
        dispute = event["data"]["object"]
    elif event["type"] == "charge.dispute.funds_reinstated":
        dispute = event["data"]["object"]
    elif event["type"] == "charge.dispute.funds_withdrawn":
        dispute = event["data"]["object"]
    elif event["type"] == "charge.dispute.updated":
        dispute = event["data"]["object"]
    elif event["type"] == "charge.refund.updated":
        refund = event["data"]["object"]
    elif event["type"] == "checkout.session.async_payment_failed":
        session = event["data"]["object"]
    elif event["type"] == "checkout.session.async_payment_succeeded":
        session = event["data"]["object"]
    elif event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
    elif event["type"] == "checkout.session.expired":
        session = event["data"]["object"]
    elif event["type"] == "coupon.created":
        coupon = event["data"]["object"]
    elif event["type"] == "coupon.deleted":
        coupon = event["data"]["object"]
    elif event["type"] == "coupon.updated":
        coupon = event["data"]["object"]
    elif event["type"] == "credit_note.created":
        credit_note = event["data"]["object"]
    elif event["type"] == "credit_note.updated":
        credit_note = event["data"]["object"]
    elif event["type"] == "credit_note.voided":
        credit_note = event["data"]["object"]
    elif event["type"] == "customer.created":
        customer = event["data"]["object"]
    elif event["type"] == "customer.deleted":
        customer = event["data"]["object"]
    elif event["type"] == "customer.updated":
        customer = event["data"]["object"]
    elif event["type"] == "customer.discount.created":
        discount = event["data"]["object"]
    elif event["type"] == "customer.discount.deleted":
        discount = event["data"]["object"]
    elif event["type"] == "customer.discount.updated":
        discount = event["data"]["object"]
    elif event["type"] == "customer.source.created":
        source = event["data"]["object"]
    elif event["type"] == "customer.source.deleted":
        source = event["data"]["object"]
    elif event["type"] == "customer.source.expiring":
        source = event["data"]["object"]
    elif event["type"] == "customer.source.updated":
        source = event["data"]["object"]
    elif event["type"] == "customer.subscription.created":
        subscription = event["data"]["object"]
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++=======================")
        print("====> Subscription Created <===", subscription, "====> Subscription <===")
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++=======================")
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        print("------------------------------------------------------------------------------------------------------")
        print("====> Subscription Deleted <===", subscription, "====> Subscription <===")
        print("-------------------------------------------------------------------------------------------------------")
    elif event["type"] == "customer.subscription.paused":
        subscription = event["data"]["object"]
    elif event["type"] == "customer.subscription.pending_update_applied":
        subscription = event["data"]["object"]
    elif event["type"] == "customer.subscription.pending_update_expired":
        subscription = event["data"]["object"]
    elif event["type"] == "customer.subscription.resumed":
        subscription = event["data"]["object"]
    elif event["type"] == "customer.subscription.trial_will_end":
        subscription = event["data"]["object"]
    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        if subscription.get("status") == "past_due":
            # Recurring Payment Failed
            PaymentAppServices().create_payment_and_update_campaign_on_failed_recurring_payment(subscription=subscription)
        if not subscription.get("cancellation_details").get("reason"):
            print(
                "=======================================================================================================")
            print("====> Subscription Updated <===\n", subscription, "====> Subscription <===")
            print(
                "=======================================================================================================")
    elif event["type"] == "customer.tax_id.created":
        tax_id = event["data"]["object"]
    elif event["type"] == "customer.tax_id.deleted":
        tax_id = event["data"]["object"]
    elif event["type"] == "customer.tax_id.updated":
        tax_id = event["data"]["object"]
    elif event["type"] == "customer_cash_balance_transaction.created":
        customer_cash_balance_transaction = event["data"]["object"]
    elif event["type"] == "file.created":
        file = event["data"]["object"]
    elif event["type"] == "financial_connections.account.created":
        account = event["data"]["object"]
    elif event["type"] == "financial_connections.account.deactivated":
        account = event["data"]["object"]
    elif event["type"] == "financial_connections.account.disconnected":
        account = event["data"]["object"]
    elif event["type"] == "financial_connections.account.reactivated":
        account = event["data"]["object"]
    elif event["type"] == "financial_connections.account.refreshed_balance":
        account = event["data"]["object"]
    elif event["type"] == "identity.verification_session.canceled":
        verification_session = event["data"]["object"]
    elif event["type"] == "identity.verification_session.created":
        verification_session = event["data"]["object"]
    elif event["type"] == "identity.verification_session.processing":
        verification_session = event["data"]["object"]
    elif event["type"] == "identity.verification_session.requires_input":
        verification_session = event["data"]["object"]
    elif event["type"] == "identity.verification_session.verified":
        verification_session = event["data"]["object"]
    elif event["type"] == "invoice.created":
        invoice = event["data"]["object"]
    elif event["type"] == "invoice.deleted":
        invoice = event["data"]["object"]
    elif event["type"] == "invoice.finalization_failed":
        invoice = event["data"]["object"]
    elif event["type"] == "invoice.finalized":
        invoice = event["data"]["object"]
    elif event["type"] == "invoice.marked_uncollectible":
        invoice = event["data"]["object"]
    elif event["type"] == "invoice.paid":
        invoice = event["data"]["object"]
    elif event["type"] == "invoice.payment_action_required":
        invoice = event["data"]["object"]
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        print("=======================================================================================================")
        print("====> Invoice Payment Failed <===\n", invoice, "====> invoice <===")
        print("=======================================================================================================")
    elif event["type"] == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        subscription_object = stripe.Subscription.retrieve(invoice.get('subscription'))
        PaymentAppServices().create_payment_and_update_campaign_on_successful_recurring_payment(
            subscription=subscription_object)
        print("=======================================================================================================")
        print("====> Invoice Payment Succeeded with Create Subscription <===\n", subscription_object,
              "====> Invoice Payment Succeeded <===")
        print("=======================================================================================================")
    elif event["type"] == "invoice.sent":
        invoice = event["data"]["object"]
    elif event["type"] == "invoice.upcoming":
        invoice = event["data"]["object"]
    elif event["type"] == "invoice.updated":
        invoice = event["data"]["object"]
    elif event["type"] == "invoice.voided":
        invoice = event["data"]["object"]
    elif event["type"] == "invoiceitem.created":
        invoiceitem = event["data"]["object"]
    elif event["type"] == "invoiceitem.deleted":
        invoiceitem = event["data"]["object"]
    elif event["type"] == "invoiceitem.updated":
        invoiceitem = event["data"]["object"]
    elif event["type"] == "issuing_authorization.created":
        issuing_authorization = event["data"]["object"]
    elif event["type"] == "issuing_authorization.updated":
        issuing_authorization = event["data"]["object"]
    elif event["type"] == "issuing_card.created":
        issuing_card = event["data"]["object"]
    elif event["type"] == "issuing_card.updated":
        issuing_card = event["data"]["object"]
    elif event["type"] == "issuing_cardholder.created":
        issuing_cardholder = event["data"]["object"]
    elif event["type"] == "issuing_cardholder.updated":
        issuing_cardholder = event["data"]["object"]
    elif event["type"] == "issuing_dispute.closed":
        issuing_dispute = event["data"]["object"]
    elif event["type"] == "issuing_dispute.created":
        issuing_dispute = event["data"]["object"]
    elif event["type"] == "issuing_dispute.funds_reinstated":
        issuing_dispute = event["data"]["object"]
    elif event["type"] == "issuing_dispute.submitted":
        issuing_dispute = event["data"]["object"]
    elif event["type"] == "issuing_dispute.updated":
        issuing_dispute = event["data"]["object"]
    elif event["type"] == "issuing_transaction.created":
        issuing_transaction = event["data"]["object"]
    elif event["type"] == "issuing_transaction.updated":
        issuing_transaction = event["data"]["object"]
    elif event["type"] == "mandate.updated":
        mandate = event["data"]["object"]
    elif event["type"] == "order.created":
        order = event["data"]["object"]
    elif event["type"] == "payment_intent.amount_capturable_updated":
        payment_intent = event["data"]["object"]
    elif event["type"] == "payment_intent.canceled":
        payment_intent = event["data"]["object"]
    elif event["type"] == "payment_intent.created":
        payment_intent = event["data"]["object"]
    elif event["type"] == "payment_intent.partially_funded":
        payment_intent = event["data"]["object"]
    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
    elif event["type"] == "payment_intent.processing":
        payment_intent = event["data"]["object"]
    elif event["type"] == "payment_intent.requires_action":
        payment_intent = event["data"]["object"]
    elif event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
    elif event["type"] == "payment_link.created":
        payment_link = event["data"]["object"]
    elif event["type"] == "payment_link.updated":
        payment_link = event["data"]["object"]
    elif event["type"] == "payment_method.attached":
        payment_method = event["data"]["object"]
        print("=======================================================================================================")
        print("====> Payment Method Attached <===\n", payment_method, "====> payment_method <===")
        print("=======================================================================================================")
    elif event["type"] == "payment_method.automatically_updated":
        payment_method = event["data"]["object"]
        print("=======================================================================================================")
        print("====> Payment Method automatically_updated <===\n", payment_method, "====> payment_method <===")
        print("=======================================================================================================")
    elif event["type"] == "payment_method.detached":
        payment_method = event["data"]["object"]
        print("=======================================================================================================")
        print("====> Payment Method Detached <===\n", payment_method, "====> payment_method <===")
        print("=======================================================================================================")
    elif event["type"] == "payment_method.updated":
        payment_method = event["data"]["object"]
        print("=======================================================================================================")
        print("====> Payment Method Updated <===\n", payment_method, "====> payment_method <===")
        print("=======================================================================================================")
    elif event["type"] == "payout.canceled":
        payout = event["data"]["object"]
    elif event["type"] == "payout.created":
        payout = event["data"]["object"]
    elif event["type"] == "payout.failed":
        payout = event["data"]["object"]
    elif event["type"] == "payout.paid":
        payout = event["data"]["object"]
    elif event["type"] == "payout.reconciliation_completed":
        payout = event["data"]["object"]
    elif event["type"] == "payout.updated":
        payout = event["data"]["object"]
    elif event["type"] == "person.created":
        person = event["data"]["object"]
    elif event["type"] == "person.deleted":
        person = event["data"]["object"]
    elif event["type"] == "person.updated":
        person = event["data"]["object"]
    elif event["type"] == "plan.created":
        plan = event["data"]["object"]
    elif event["type"] == "plan.deleted":
        plan = event["data"]["object"]
    elif event["type"] == "plan.updated":
        plan = event["data"]["object"]
    elif event["type"] == "price.created":
        price = event["data"]["object"]
    elif event["type"] == "price.deleted":
        price = event["data"]["object"]
    elif event["type"] == "price.updated":
        price = event["data"]["object"]
    elif event["type"] == "product.created":
        product = event["data"]["object"]
    elif event["type"] == "product.deleted":
        product = event["data"]["object"]
    elif event["type"] == "product.updated":
        product = event["data"]["object"]
    elif event["type"] == "promotion_code.created":
        promotion_code = event["data"]["object"]
    elif event["type"] == "promotion_code.updated":
        promotion_code = event["data"]["object"]
    elif event["type"] == "quote.accepted":
        quote = event["data"]["object"]
    elif event["type"] == "quote.canceled":
        quote = event["data"]["object"]
    elif event["type"] == "quote.created":
        quote = event["data"]["object"]
    elif event["type"] == "quote.finalized":
        quote = event["data"]["object"]
    elif event["type"] == "radar.early_fraud_warning.created":
        early_fraud_warning = event["data"]["object"]
    elif event["type"] == "radar.early_fraud_warning.updated":
        early_fraud_warning = event["data"]["object"]
    elif event["type"] == "recipient.created":
        recipient = event["data"]["object"]
    elif event["type"] == "recipient.deleted":
        recipient = event["data"]["object"]
    elif event["type"] == "recipient.updated":
        recipient = event["data"]["object"]
    elif event["type"] == "refund.created":
        refund = event["data"]["object"]
    elif event["type"] == "refund.updated":
        refund = event["data"]["object"]
    elif event["type"] == "reporting.report_run.failed":
        report_run = event["data"]["object"]
    elif event["type"] == "reporting.report_run.succeeded":
        report_run = event["data"]["object"]
    elif event["type"] == "review.closed":
        review = event["data"]["object"]
    elif event["type"] == "review.opened":
        review = event["data"]["object"]
    elif event["type"] == "setup_intent.canceled":
        setup_intent = event["data"]["object"]
    elif event["type"] == "setup_intent.created":
        setup_intent = event["data"]["object"]
    elif event["type"] == "setup_intent.requires_action":
        setup_intent = event["data"]["object"]
    elif event["type"] == "setup_intent.setup_failed":
        setup_intent = event["data"]["object"]
    elif event["type"] == "setup_intent.succeeded":
        setup_intent = event["data"]["object"]
    elif event["type"] == "sigma.scheduled_query_run.created":
        scheduled_query_run = event["data"]["object"]
    elif event["type"] == "sku.created":
        sku = event["data"]["object"]
    elif event["type"] == "sku.deleted":
        sku = event["data"]["object"]
    elif event["type"] == "sku.updated":
        sku = event["data"]["object"]
    elif event["type"] == "source.canceled":
        source = event["data"]["object"]
    elif event["type"] == "source.chargeable":
        source = event["data"]["object"]
    elif event["type"] == "source.failed":
        source = event["data"]["object"]
    elif event["type"] == "source.mandate_notification":
        source = event["data"]["object"]
    elif event["type"] == "source.refund_attributes_required":
        source = event["data"]["object"]
    elif event["type"] == "source.transaction.created":
        transaction = event["data"]["object"]
    elif event["type"] == "source.transaction.updated":
        transaction = event["data"]["object"]
    elif event["type"] == "subscription_schedule.aborted":
        subscription_schedule = event["data"]["object"]
    elif event["type"] == "subscription_schedule.canceled":
        subscription_schedule = event["data"]["object"]
    elif event["type"] == "subscription_schedule.completed":
        subscription_schedule = event["data"]["object"]
    elif event["type"] == "subscription_schedule.created":
        subscription_schedule = event["data"]["object"]
    elif event["type"] == "subscription_schedule.expiring":
        subscription_schedule = event["data"]["object"]
    elif event["type"] == "subscription_schedule.released":
        subscription_schedule = event["data"]["object"]
    elif event["type"] == "subscription_schedule.updated":
        subscription_schedule = event["data"]["object"]
    elif event["type"] == "tax_rate.created":
        tax_rate = event["data"]["object"]
    elif event["type"] == "tax_rate.updated":
        tax_rate = event["data"]["object"]
    elif event["type"] == "terminal.reader.action_failed":
        reader = event["data"]["object"]
    elif event["type"] == "terminal.reader.action_succeeded":
        reader = event["data"]["object"]
    elif event["type"] == "test_helpers.test_clock.advancing":
        test_clock = event["data"]["object"]
    elif event["type"] == "test_helpers.test_clock.created":
        test_clock = event["data"]["object"]
    elif event["type"] == "test_helpers.test_clock.deleted":
        test_clock = event["data"]["object"]
    elif event["type"] == "test_helpers.test_clock.internal_failure":
        test_clock = event["data"]["object"]
    elif event["type"] == "test_helpers.test_clock.ready":
        test_clock = event["data"]["object"]
    elif event["type"] == "topup.canceled":
        topup = event["data"]["object"]
    elif event["type"] == "topup.created":
        topup = event["data"]["object"]
    elif event["type"] == "topup.failed":
        topup = event["data"]["object"]
    elif event["type"] == "topup.reversed":
        topup = event["data"]["object"]
    elif event["type"] == "topup.succeeded":
        topup = event["data"]["object"]
    elif event["type"] == "transfer.created":
        transfer = event["data"]["object"]
    elif event["type"] == "transfer.reversed":
        transfer = event["data"]["object"]
    elif event["type"] == "transfer.updated":
        transfer = event["data"]["object"]
    else:
        # TODO : Add Logger For Unhandled Events
        print("Unhandled event type {}".format(event["type"]))

    return HttpResponse(status=200)

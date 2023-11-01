import json

from django.db import models
from django.views import View
from django.contrib import messages
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Subquery, OuterRef, F, ExpressionWrapper, IntegerField, Q

from embermail.domain.campaigns.models import Campaign
from utils.middleware.middleware import MasterUserMiddleware
from embermail.application.payments.services import PaymentAppServices
from embermail.application.profiles.services import ProfileAppServices
from embermail.application.campaigns.services import CampaignAppServices
from utils.django.exceptions import ValidationException, PasswordNotMatched


class UserProfileView(LoginRequiredMixin, View):
    """
    User Can Update Name and Password
    """

    def get(self, request):
        """
        Render User Profile Page
        """
        user = request.user
        context = {
            "user": user,
        }
        return render(request, 'profiles/user_profile.html', context=context)

    def post(self, request):
        """
        Update User's Name and Change Password by AJAX Post Method
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            data_dict = json.load(request)
            data_dict['user'] = request.user
            try:
                if data_dict.get('input_name'):
                    ProfileAppServices().update_user_profile_by_name(data_dict=data_dict)
                    message = "Name Updated Successfully."
                    messages.success(request, message)
                    return JsonResponse({'status': True})
                else:
                    ProfileAppServices().change_password(data_dict=data_dict)
                    message = "Password Changed Successfully."
                    messages.success(request, message)
                    return JsonResponse({'status': True})

            except ValidationException as ve:
                return JsonResponse({'error_message': ve.message, 'error_tag': ve.item.get('error_tag')})
            except PasswordNotMatched as pnm:
                return JsonResponse({'error_message': pnm.message, 'error_tag': pnm.item.get('error_tag')})
            except Exception as e:
                message = "Something went wrong while updating user profile."
                messages.error(request, message)
                return JsonResponse({'redirect': "/profiles/user-profile/", 'error': e.args})


class MemberListView(View):
    """
    Member Listing
    """

    def get(self, request):
        """
        List All Members which are Registered under Master User ID
        """
        try:
            master_user_id = request.user.id

            members = Campaign.objects.raw(
                f"SELECT c.id, c.master_user_id, c.user_id, c.email, c.app_password, c.plan_id, c.next_invoice_date, c.domain_type, CASE c.domain_type WHEN 'custom' THEN 'Custom' WHEN 'new_domain' THEN 'Warm up new email' WHEN 'repair' THEN 'Repair Reputation' WHEN 'maintain_deliverability' THEN 'Maintain Deliverability' END AS updated_domain_type, CASE WHEN c.user_id is NULL THEN 'Invitation Pending' WHEN c.app_password is NULL THEN 'App Password Required' ELSE 'Active' END AS status, u.first_name, p.name, p.plan_amount, p.plan_duration, p.plan_amount/p.plan_duration AS plan_charge_per_month from campaign as c FULL JOIN plan as p ON c.plan_id = p.id LEFT JOIN public.user as u ON c.email=u.email where c.master_user_id='{master_user_id}' and (c.master_user_id<>c.user_id or c.user_id IS NULL)")

            context = {
                'members': members
            }
            return render(request, 'profiles/member_list.html', context=context)
        except Exception as e:
            print(e.args)

    def post(self, request):
        """
        Get Detail View for Campaign by Campaign ID
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            campaign_id = json.load(request).get('campaign_id')
            master_user_id = request.user.id
            try:
                if request.user.is_master_user:
                    campaign = Campaign.objects.raw(
                        f"SELECT c.id, c.master_user_id, c.user_id, c.email, c.app_password, c.plan_id, c.next_invoice_date, c.domain_type, CASE c.domain_type WHEN 'custom' THEN 'Custom' WHEN 'new_domain' THEN 'Warm up new email' WHEN 'repair' THEN 'Repair Reputation' WHEN 'maintain_deliverability' THEN 'Maintain Deliverability' END AS updated_domain_type, CASE WHEN c.user_id is NULL THEN 'Invitation Pending' WHEN c.app_password is NULL THEN 'App Password Required' ELSE 'Active' END AS status, u.first_name, p.name, p.plan_amount, p.plan_duration, p.plan_amount/p.plan_duration AS plan_charge_per_month from campaign as c FULL JOIN plan as p ON c.plan_id = p.id LEFT JOIN public.user as u ON c.email=u.email where c.master_user_id='{master_user_id}' and (c.master_user_id<>c.user_id or c.user_id IS NULL) and c.id='{campaign_id}'")[
                        0]
                    campaign_dict = dict()
                    campaign_dict['email'] = campaign.email
                    campaign_dict['user_id'] = str(campaign.user_id) if campaign.user_id else ""
                    campaign_dict['first_name'] = campaign.first_name
                    campaign_dict['plan_name'] = campaign.name
                    campaign_dict['plan_amount'] = campaign.plan_charge_per_month
                    campaign_dict['status'] = campaign.status
                    campaign_dict['domain_type'] = campaign.updated_domain_type
                    campaign_dict['next_invoice'] = campaign.next_invoice_date.strftime("%d-%b-%y")

                    return JsonResponse({'campaign': json.dumps(campaign_dict)})
            except Exception as e:
                message = "Something went wrong while fetching member."
                messages.error(request, message)
                return JsonResponse({'redirect': "/profiles/member/list/", 'error': e.args})

    @method_decorator(MasterUserMiddleware)
    def dispatch(self, request, *args, **kwargs):
        return super(self.__class__, self).dispatch(request, *args, **kwargs)


class BillingSectionView(View):
    """
    Listing of Plans, Payment Methods and Payment History
    """

    def get(self, request):
        """
        Renders Plans, Payments Methods and Payment History
        """
        master_user_id = request.user.id

        plans = PaymentAppServices().list_plans().filter(is_active=True).annotate(
            plan_amount_per_month=ExpressionWrapper(F('plan_amount') / F('plan_duration'),
                                                    output_field=IntegerField())).annotate(total_campaign=Subquery(
            CampaignAppServices().list_campaigns_by_master_user_id(master_user_id=request.user.id).filter(
                plan_id=OuterRef('id')).values("plan_id").annotate(campaign_count=Count('id')).values('campaign_count'),
            output_field=models.IntegerField())).order_by('plan_duration')

        payment_methods = PaymentAppServices().list_payment_methods_by_master_user_id(
            master_user_id=master_user_id).values('stripe_payment_method__card__brand',
                                                  'stripe_payment_method__card__last4',
                                                  'stripe_payment_method__card__exp_year',
                                                  'stripe_payment_method__card__exp_month').annotate(
            card_brand=F('stripe_payment_method__card__brand'), card_last4=F('stripe_payment_method__card__last4'),
            card_expiry_month=F('stripe_payment_method__card__exp_month'),
            card_expiry_year=F('stripe_payment_method__card__exp_year'))

        invoices = PaymentAppServices().list_payments_by_master_user_id(master_user_id=master_user_id)

        invoices = invoices.values('id',
                                   'warmup_email',
                                   'master_user_id',
                                   'payment_status',
                                   'stripe_subscription__current_period_start',
                                   'stripe_subscription__items__data__0__price__unit_amount',
                                   'stripe_subscription__latest_invoice', 'invoice_download_url', 'invoice_name')

        invoices = invoices.annotate(invoice_date=F('stripe_subscription__current_period_start'),
                                     plan_price=F('stripe_subscription__items__data__0__price__unit_amount'))

        context = {
            'plans': plans,
            'payment_methods': payment_methods,
            'invoices': invoices,

        }
        return render(request, 'profiles/billing_section.html', context=context)


class MemberListAJAXView(View):
    """
    Searching for Member List by Name, Email and Plan
    """

    def post(self, request):
        """
        Return Table body Html Template to append to Table
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            search_value = json.load(request).get('search_value')

            master_user_id = request.user.id
            members = Campaign.objects.raw(
                f"""SELECT c.id, c.master_user_id, c.user_id, c.email, c.app_password, c.plan_id, c.next_invoice_date, c.domain_type, CASE c.domain_type WHEN 'custom' THEN 'Custom' WHEN 'new_domain' THEN 'Warm up new email' WHEN 'repair' THEN 'Repair Reputation' WHEN 'maintain_deliverability' THEN 'Maintain Deliverability' END AS updated_domain_type, CASE WHEN c.user_id is NULL THEN 'Invitation Pending' WHEN c.app_password is NULL THEN 'App Password Required' ELSE 'Active' END AS status, u.first_name, p.name, p.plan_amount, p.plan_duration, p.plan_amount/p.plan_duration AS plan_charge_per_month from campaign as c FULL JOIN plan as p ON c.plan_id = p.id LEFT JOIN public.user as u ON c.email=u.email where c.master_user_id=%s and (c.master_user_id<>c.user_id or c.user_id IS NULL) and (u.first_name LIKE %s OR c.email LIKE %s OR p.name LIKE %s)""",
                [master_user_id, f'%{search_value}%', f'%{search_value}%', f'%{search_value}%'])

            # members.filter(Q(first_name__icontains=search_value) | Q(email__icontains=search_value) | Q(
            #     name__icontains=search_value))

            context = {
                'members': members
            }
            return render(request, 'profiles/member_list_tbody.html', context=context)


class BillingSearchAJAXView(View):
    """
    Searching For Payment History Post AJAX View
    """

    def post(self, request):
        """
        Return Payment History Filtered by Searched Value using AJAX Post Method
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            search_value = json.load(request).get('search_value')
            invoices = PaymentAppServices().list_payments_by_master_user_id(master_user_id=request.user.id).filter(
                Q(warmup_email__icontains=search_value) | Q(invoice_name__icontains=search_value))
            invoices = invoices.values('id',
                                       'warmup_email',
                                       'master_user_id',
                                       'payment_status',
                                       'stripe_subscription__current_period_start',
                                       'stripe_subscription__items__data__0__price__unit_amount',
                                       'stripe_subscription__latest_invoice', 'invoice_download_url', 'invoice_name')

            invoices = list(invoices.annotate(invoice_date=F('stripe_subscription__current_period_start'),
                                              plan_price=F('stripe_subscription__items__data__0__price__unit_amount')))
            context = {
                'invoices': invoices,
            }
            return render(request, 'profiles/billing_invoice_table.html', context=context)

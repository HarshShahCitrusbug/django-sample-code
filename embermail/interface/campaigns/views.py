import datetime
import uuid
import json
import random
import logging

import pandas as pd
from django.views import View
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.db.models import Subquery, OuterRef
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site

from embermail.domain.campaigns.models import Campaign
from embermail.domain.templates.models import Template, Thread
from embermail.domain.templates.services import ThreadServices, TemplateServices
from utils.data_manipulation.encryption import SecretEncryption
from embermail.infrastructure.logger.models import AttributeLogger
from embermail.domain.text_choices import CampaignActionRequiredChoices
from embermail.application.campaigns.services import CampaignAppServices
from embermail.application.payments.services import PaymentAppServices, StripeAppServices
from embermail.interface.campaigns.tasks import send_email_task_schedular, time_counter, \
    create_campaign_reports_by_log_records
from utils.django.exceptions import CampaignDataValidation, CampaignDoesNotExist, InvalidCredentialsException, \
    ValidationException, CampaignAlreadyExist, \
    CampaignCreationException, PaymentDoesNotExist, StripeSubscriptionException, \
    SendgridEmailException, ActionRequiredException

log = AttributeLogger(logging.getLogger(__name__))


class ReadyToStartView(LoginRequiredMixin, View):
    """
    View for Displaying List of Campaigns if Exist and Render Ready to Start Page
    """

    def get(self, request):
        """
        Display List of Campaigns if Exist and Render Ready to Start Page
        """
        try:
            log.info(msg="Rendering Ready to Start Page.")
            campaign_list = list(
                CampaignAppServices().list_campaigns_by_user_id(user_id=request.user.id).values('email',
                                                                                                'email_service_provider',
                                                                                                'master_user_id'))
            if request.user.is_master_user:
                campaign_list = list(
                    CampaignAppServices().list_campaigns_by_master_user_id(master_user_id=request.user.id).values(
                        'email', 'email_service_provider', 'master_user_id'))

            if campaign_list:
                log.info(msg="Campaign Exist for user and redirecting to Campaign List.")
                return redirect('campaigns:list')
            log.info(msg="Campaign not Exist for user and redirecting to Ready to Start Page.")
            return render(request, 'campaigns/ready_to_start.html')
        except Exception as e:
            log.error(msg="Something went wrong while getting list of campaigns or rendering ready-to-start page.")
            return render(request, '404.html')  # TODO: Return 404 Error Page


class SelectProviderView(LoginRequiredMixin, View):
    """
    View for Selecting Email Provider
    """

    def get(self, request):
        log.info(msg="Entered into Select Email Provider Page.")
        # Deleting All Django Sessions for New Campaign Flow
        if 'selected_flow' in request.session:
            del request.session["selected_flow"]
            log.info(msg="selected_flow deleted from Django Session from SelectorProviderView.")
        if 'email_provider' in request.session:
            del request.session["email_provider"]
            log.info(msg="email_provider deleted from Django Session from SelectorProviderView.")
        if 'warmup_email_address' in request.session:
            del request.session["warmup_email_address"]
            log.info(msg="warmup_email_address deleted from Django Session from SelectorProviderView.")
        if 'selected_plan_id' in request.session:
            del request.session["selected_plan_id"]
            log.info(msg="selected_plan_id deleted from Django Session from SelectorProviderView.")
        if 'selected_flow' in request.session:
            del request.session["selected_flow"]
            log.info(msg="selected_flow deleted from Django Session from SelectorProviderView.")

        selected_flow = self.request.GET.get('selected_flow')
        request.session['selected_flow'] = selected_flow
        context = {
            'selected_flow': selected_flow
        }
        log.info(msg="Rendering Select Email Provider Page with selected_flow context.")
        return render(request, 'campaigns/selector_provider.html', context=context)


class AddEmailView(LoginRequiredMixin, View):
    """
    View for Adding Email and If Invite Flow then create Campaigns and redirect to Payment
    """

    def get(self, request):
        """
        Render Add Email Page
        """
        log.info(msg="Entered into Add Email Page.")
        selected_flow = self.request.GET.get('selected_flow')
        email_provider = self.request.GET.get('email_provider')
        request.session['email_provider'] = email_provider
        context = {
            'selected_flow': selected_flow,
            'email_provider': email_provider,
        }
        log.info(msg="Rendering Add Email Page with selected_flow and email_provider context.")
        return render(request, 'campaigns/add_email.html', context=context)

    def post(self, request):
        """
        Validating and Checking Warmup Email is Exist for Inbox Flow
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            log.info(msg="Entered into Add Email AJAX Post Method for Add Inbox Flow..")
            try:
                data_dict = json.load(request)
                selected_flow = data_dict.get('selected_flow')
                email_provider = data_dict.get('email_provider')
                email = data_dict.get('email')
                request.session['warmup_email_address'] = email
                data_dict['user'] = request.user
                CampaignAppServices().validate_email_and_check_campaign_exist(data_dict=data_dict)
                if selected_flow == 'inbox':
                    log.info(
                        msg="Email Validated and is not exist in campaign and redirecting to IMAP Access Detail Page.")
                    return JsonResponse({
                        "redirect": f'/campaigns/imap-access-details/?selected_flow={selected_flow}&email_provider={email_provider}&email={email}'})
                else:
                    log.info(
                        msg="Email Validated and is not exist in campaign and redirecting to Plan Selection Page.")
                    return JsonResponse({
                        "redirect": f'/payment/plan/selection/'})
            except ValidationException as ve:
                log.error(msg=ve.message)
                return JsonResponse({'error_message': ve.message, 'error_tag': ve.item.get('error_tag')})
            except CampaignAlreadyExist as cae:
                log.error(msg=cae.message)
                return JsonResponse({'error_message': cae.message, 'error_tag': cae.item.get('error_tag')})
            except Exception as e:
                message = "Something went wrong while Adding Warmup Email."
                log.error(msg=f"{message} and Error: {e.args}")
                return JsonResponse({'error_message': message, 'error': e.args})
        log.error(msg="Something went wrong in Add Email AJAX Post Method and Rendering to 404 Page.")
        return render(request, '404.html')  # TODO : Return 404 Error Page


class ImapAccessDetailView(LoginRequiredMixin, View):
    """
    View for Displaying Details of Giving Access to IMAP
    """

    def get(self, request):
        """
        Renders IMAP Access Details Page
        """
        log.info(msg="Enter into IMAP Access Detail Page.")
        selected_flow = self.request.GET.get('selected_flow')
        email_provider = self.request.GET.get('email_provider')
        email = self.request.GET.get('email')

        sign_in_link = getattr(settings, "OUTLOOK_SIGN_IN_LINK", "#")
        imap_access_link = getattr(settings, "OUTLOOK_IMAP_ACCESS_LINK", "#")
        if email_provider == 'gmail':
            sign_in_link = getattr(settings, "GMAIL_SIGN_IN_LINK", "#")
            imap_access_link = getattr(settings, "GMAIL_IMAP_ACCESS_LINK", "#")
        context = {
            'selected_flow': selected_flow,
            'email_provider': email_provider,
            'email': email,
            'sign_in_link': sign_in_link,
            'imap_access_link': imap_access_link,
        }
        log.info(
            msg="Rendering IMAP Access Detail Page with selected_flow, email_provider, email_sign_in_link and imap_access_link context.")
        return render(request, 'campaigns/imap_access_points.html', context=context)


class JoiningImapAccessDetailView(LoginRequiredMixin, View):
    """
    View for Displaying Details of Giving Access to IMAP for Joining Flow
    """

    def get(self, request):
        """
        Renders IMAP Access Details Page for Joining Flow
        """
        try:
            log.info(msg="Entering into Imap Access Detail Page for Join Team Flow.")
            email = request.user.email
            campaign = CampaignAppServices().get_campaign_by_email(email=email)
            email_provider = campaign.email_service_provider
            sign_in_link = getattr(settings, "OUTLOOK_SIGN_IN_LINK", "#")
            imap_access_link = getattr(settings, "OUTLOOK_IMAP_ACCESS_LINK", "#")
            if email_provider == 'gmail':
                sign_in_link = getattr(settings, "GMAIL_SIGN_IN_LINK", "#")
                imap_access_link = getattr(settings, "GMAIL_IMAP_ACCESS_LINK", "#")

            context = {
                'email_provider': email_provider,
                'email': email,
                'sign_in_link': sign_in_link,
                'imap_access_link': imap_access_link,
            }
            log.info(
                msg="Rendering Imap Access Detail Page for Join Team Flow with email_provider, email, sign_in_link, imap_access_detail context.")
            return render(request, 'campaigns/joining_imap_access_points.html', context=context)
        except Exception as e:
            log.error(msg="Something went wrong in Imap Access Detail Page for Join Team Flow and Rendering to 404.")
            return render(request, '404.html')  # TODO : Return 404 Error Page


class AddAppPasswordView(LoginRequiredMixin, View):
    """
    View for Displaying App Password Input and Create Campaigns for Inbox Flow
    """

    def get(self, request):
        """
        Renders Add App Password Page
        """
        log.info(msg="Entering into Add AppPassword for Inbox Flow.")
        selected_flow = self.request.GET.get('selected_flow')
        email_provider = self.request.GET.get('email_provider')
        email = self.request.GET.get('email')

        two_step_verification_link = getattr(settings, "OUTLOOK_TWO_STEP_VERIFICATION", "#")
        app_password_link = getattr(settings, "OUTLOOK_APP_PASSWORD", "#")
        if email_provider == 'gmail':
            two_step_verification_link = getattr(settings, "GMAIL_TWO_STEP_VERIFICATION", "#")
            app_password_link = getattr(settings, "GMAIL_APP_PASSWORD", "#")
        context = {
            'selected_flow': selected_flow,
            'email_provider': email_provider,
            'email': email,
            'two_step_verification_link': two_step_verification_link,
            'app_password_link': app_password_link,
        }
        log.info(msg="Rendering Add AppPassword for Inbox Flow with context.")
        return render(request, 'campaigns/add_app_password.html', context=context)

    def post(self, request):
        """
        Creating Campaign with App Password for Inbox Flow
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            log.info(msg="Entered into Add App Password Post AJAX Method for Creating Campaign for Inbox Flow.")
            try:
                data_dict = json.load(request)
                data_dict['master_user_id'] = request.user.id
                email = data_dict.get('email')
                request.session['warmup_email_address'] = email

                # Create Campaign if not exists
                CampaignAppServices().create_campaign_by_dict(data_dict=data_dict)
                log.info(msg=f"Campaign Created with {email} for Inbox Flow.")
                return JsonResponse({"valid_credentials": True})
            except ValidationException as ve:
                log.error(msg=ve.message)
                return JsonResponse(
                    {'error_message': ve.message, 'error_tag': ve.item.get('error_tag'), 'error': ve.item.get('error')})
            except InvalidCredentialsException as ivce:
                log.error(msg=ivce.message)
                return JsonResponse({'error_message': ivce.message, 'error_tag': ivce.item.get('error_tag'),
                                     'error': ivce.item.get('error')})
            except CampaignAlreadyExist as cae:
                log.error(msg=cae.message)
                return JsonResponse({'error_message': cae.message, 'error_tag': cae.item.get('error_tag'),
                                     'error': cae.item.get('error')})
            except CampaignCreationException as cce:
                log.error(msg=cce.message)
                return JsonResponse({'error_message': cce.message, 'error_tag': cce.item.get('error_tag'),
                                     'error': cce.item.get('error')})
            except Exception as e:
                message = "Something went wrong while Creating Campaign"
                log.error(msg=f"{message} and Error: {e.args}")
                return JsonResponse(data={'error_message': message, 'error': e.args})
        log.error(msg="Something went wrong in Add App Password AJAX post Method.")
        return render(request, '404.html')  # TODO : Return 404 Error Page


class JoiningAddAppPasswordView(LoginRequiredMixin, View):
    """
    View for Displaying App Password Input and Update Campaign by App Password for Joining Flow
    """

    def get(self, request):
        """
        Renders Add App Password Page
        """
        try:
            log.info(msg="Entering into Add App Password for Join Team Flow.")
            email = request.user.email
            campaign = CampaignAppServices().get_campaign_by_email(email=email)
            email_provider = campaign.email_service_provider

            two_step_verification_link = getattr(settings, "OUTLOOK_TWO_STEP_VERIFICATION", "#")
            app_password_link = getattr(settings, "OUTLOOK_APP_PASSWORD", "#")
            if email_provider == 'gmail':
                two_step_verification_link = getattr(settings, "GMAIL_TWO_STEP_VERIFICATION", "#")
                app_password_link = getattr(settings, "GMAIL_APP_PASSWORD", "#")

            context = {
                'email_provider': email_provider,
                'email': email,
                'two_step_verification_link': two_step_verification_link,
                'app_password_link': app_password_link,
            }
            log.info(msg="Rendering Add App Password Page for Join Team Flow with context.")
            return render(request, 'campaigns/joining_add_app_password.html', context=context)
        except Exception as e:
            log.error(
                msg=f"Something went wrong in Add App Password Get Method for Joijn Team Flow and Error: {e.args} and rendering to 404.")
            return render(request, '404.html')  # TODO : Return 404 Error Page

    def post(self, request):
        """
        Creating Campaign with App Password for Inbox Flow
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            try:
                log.info(msg="Entered into Add App Password Post AJAX Method for Join Flow.")
                app_password = json.load(request).get('app_password')
                email = request.user.email
                data_dict = {
                    'app_password': app_password,
                    'email': email
                }
                CampaignAppServices().update_campaign_by_app_password_for_joining_flow(data_dict=data_dict)
                log.info(msg="Updated App Password for Campaign for Join Flow.")
                return JsonResponse({"success": True})
            except InvalidCredentialsException as ivce:
                log.error(msg=ivce.message)
                return JsonResponse({'error_message': ivce.message, 'error_tag': ivce.item.get('error_tag'),
                                     'error': ivce.item.get('error')})
            except Exception as e:
                message = "Something went wrong while updating App Password."
                log.error(msg=f"{message} and Error: {e.args}")
                return JsonResponse(data={'error_message': message, 'error': e.args, 'error_tag': "404"})
        log.error(msg="Something went wrong in Add App Password AJAX Post Method for Join Team.")
        return render(request, '404.html')  # TODO : Return 404 Error Page


class UpdateCampaignView(LoginRequiredMixin, View):
    """
    View for Updating Campaign Data for Inbox, Invite Flow and Edited through Campaign Listing Page.
    """

    def get(self, request):
        """
        Renders Campaign Update Page for Max Emails per day and Step up
        """
        email = request.GET.get('email', None)
        if email:
            login_user_id = request.user.id
            if CampaignAppServices().check_campaign_owner_by_email(login_user_id=login_user_id, email=email):
                request.session['warmup_email_address'] = email
            else:
                messages.error(request, "Access Denied.")
                return redirect("campaigns:list")
        log.info(msg="Entering into Campaign Update Page.")
        campaign_types = CampaignAppServices().list_campaign_types().order_by('max_emails_per_day').values('name',
                                                                                                           'display_name',
                                                                                                           'max_emails_per_day',
                                                                                                           'step_up')
        context = {
            'campaign_types': campaign_types,
        }
        log.info(msg="Rendering Campaign Update Page with campaign_types context.")
        return render(request, 'campaigns/update_campaign.html', context=context)

    def post(self, request):
        """
        Update Campaign data by Master User for Inbox and Invite Flow and Edited through Campaign Listing Page.
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            log.info(msg="Entering into Campaign Update AJAX Post Method.")
            try:
                data_dict = json.load(request)

                warmup_email = request.session.get('warmup_email_address')
                selected_flow = request.session.get('selected_flow')

                current_site = get_current_site(request)
                data_dict['warmup_email'] = warmup_email
                data_dict['master_user_id'] = request.user.id
                data_dict['current_site'] = current_site
                data_dict['selected_flow'] = selected_flow

                # Update Campaign
                campaign = CampaignAppServices().update_campaign_by_emails_per_day_and_step_up(data_dict=data_dict)
                if campaign:
                    # Delete warmup_email_address, selected_flow, email_provider from Django Session
                    if 'warmup_email_address' in request.session:
                        del request.session["warmup_email_address"]
                        log.info(msg="warmup_email_address deleted from Django Session.")

                    if 'selected_flow' in request.session:
                        del request.session["selected_flow"]
                        log.info(msg="selected_flow deleted from Django Session.")

                    if 'email_provider' in request.session:
                        del request.session["email_provider"]
                        log.info(msg="email_provider deleted from Django Session.")

                if selected_flow == "inbox":
                    log.info(msg="Campaign Updated Successfully for Inbox Flow and rendering to Home Page.")
                    messages.success(request, f"Email Warm up Started for {warmup_email}.")
                elif selected_flow == 'invite':
                    log.info(msg="Campaign Updated Successfully for Invite Flow and rendering to Home Page.")
                    messages.success(request, f"Invitation link has been sent to {warmup_email}.")
                else:
                    # When Updated through Campaign listing Detail Edit Button
                    log.info(msg="Campaign Updated Successfully and rendering to Campaign List.")
                    messages.success(request, f"Warmup Data Updated for {warmup_email}.")
                    return JsonResponse({"redirect": '/campaigns/list/'})
                return JsonResponse({"redirect": '/home/'})

            except CampaignDoesNotExist as cdne:
                log.error(msg=cdne.message)
                return JsonResponse({'error_message': cdne.message, 'error_tag': cdne.item.get('error_tag'),
                                     'error': cdne.item.get('error')})
            except SendgridEmailException as sgee:
                log.error(msg=sgee.message)
                messages.error(request, sgee.message)
                return JsonResponse({'error_message': sgee.message, 'error_tag': sgee.item.get('error_tag'),
                                     'error': sgee.item.get('error')})
            except CampaignDataValidation as cdv:
                log.error(msg=cdv.message)
                return JsonResponse({'error_message': cdv.message, 'error_tag': cdv.item.get('error_tag'),
                                     'error': cdv.item.get('error')})


class JoiningUpdateCampaignView(LoginRequiredMixin, View):
    """
    View for Updating Campaign Data for Joining User
    """

    def get(self, request):
        """
        Renders Campaign Update Page for Max Emails per day and Step up for Joining User
        """
        log.info(msg="Entered into Update Campaign Page for Join Team Flow.")
        campaign_types = CampaignAppServices().list_campaign_types().order_by('max_emails_per_day').values('name',
                                                                                                           'display_name',
                                                                                                           'max_emails_per_day',
                                                                                                           'step_up')
        context = {
            'campaign_types': campaign_types,
            'joining_flow': True,
        }
        log.info(msg="Rendering Update Campaign Page for Join Team Flow with campaign_type and joining_flow context.")
        return render(request, 'campaigns/update_campaign.html', context=context)

    def post(self, request):
        """
        Update Campaign data for Joining Team Flow
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            log.info(msg="Entered into Update Campaign AJAX Post Method for Join Team Flow.")
            try:
                data_dict = json.load(request)
                email = request.user.email
                data_dict['warmup_email'] = email
                data_dict['is_master_user'] = request.user.is_master_user

                # Update Campaign
                CampaignAppServices().update_campaign_by_emails_per_day_and_step_up(data_dict=data_dict)

                messages.success(request, f"Email Warm up Started for {email}.")
                log.info(msg=f"Campaign({email}) Updated successfully for Join Team Flow and Rendering to Home Page.")
                return JsonResponse({"redirect": '/home/'})  # TODO : Redirect

            except CampaignDoesNotExist as cdne:
                log.error(msg=cdne.message)
                return JsonResponse({'error_message': cdne.message, 'error_tag': cdne.item.get('error_tag'),
                                     'error': cdne.item.get('error')})
            except CampaignDataValidation as cdv:
                log.error(msg=cdv.message)
                return JsonResponse({'error_message': cdv.message, 'error_tag': cdv.item.get('error_tag'),
                                     'error': cdv.item.get('error')})


class CampaignListView(LoginRequiredMixin, View):
    """
    View for Listing Campaigns Registered under Master User
    """

    def get(self, request):
        """
        Renders Campaign List Page
        """
        try:
            log.info(msg="Entered into Campaign List Page.")
            user = request.user
            master_user_id = user_id = user.id
            campaigns = Campaign.objects.raw(
                f"SELECT c.id, c.email, c.email_service_provider, c.domain_type, c.next_invoice_date, p.name, CASE c.domain_type WHEN 'custom' THEN 'Custom' WHEN 'new_domain' THEN 'Warmup New Email' WHEN 'repair' THEN 'Repair Reputation' WHEN 'maintain_deliverability' THEN 'Maintain Deliverability' END AS updated_domain_type, CASE WHEN p.name IS NOT NULL THEN p.name ELSE 'Payment Required' END AS plan_name, CASE WHEN c.is_stopped IS TRUE THEN 'Paused' ELSE 'Running' END AS campaign_status, CASE WHEN c.master_user_id=c.user_id THEN 'self' ELSE 'invited' END AS campaign_owner FROM campaign as c LEFT JOIN plan as p ON c.plan_id = p.id WHERE master_user_id=%s OR user_id=%s ORDER BY c.email",
                [master_user_id, user_id])
            if not campaigns:
                if not user.is_master_user:
                    return redirect('campaigns:joining_imap_details')
                return render(request, 'campaigns/ready_to_start.html')
            context = {
                'campaigns': campaigns,
            }
            log.info(msg="Rendering Campaign List Page for with campaigns context.")
            return render(request, 'campaigns/campaign_list.html', context=context)
        except Exception as e:
            print(e)

    def post(self, request):
        """
        Update Campaign Running Status and Edit Campaign Configurations
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            try:
                data_dict = json.load(request)
                ajax_call_for = data_dict.get('ajax_call_for')
                if ajax_call_for == 'play_pause':
                    data_dict['user'] = request.user
                    campaign = CampaignAppServices().update_campaign_by_campaign_running_status_is_stopped(
                        data_dict=data_dict)
                    message = f"{campaign.email} Running Status Updated."
                    messages.success(request, message=message)
                    return JsonResponse({'success': True})
                if ajax_call_for == 'edit':
                    campaign_id = uuid.UUID(data_dict.get('campaign_id'))
                    campaign = Campaign.objects.raw(
                        f"SELECT c.id, c.email, c.user_id, c.email_service_provider, c.next_invoice_date, c.domain_type, c.is_cancelled, CASE c.domain_type WHEN 'custom' THEN 'Custom' WHEN 'new_domain' THEN 'Warmup New Email' WHEN 'repair' THEN 'Repair Reputation' WHEN 'maintain_deliverability' THEN 'Maintain Deliverability' END AS updated_domain_type, CASE WHEN p.name IS NOT NULL THEN p.name ELSE 'Payment Required' END AS plan_name, CASE WHEN c.is_stopped IS TRUE THEN 'Paused' ELSE 'Running' END AS campaign_status, p.name, p.plan_amount, p.plan_duration, p.plan_amount/p.plan_duration AS plan_charge_per_month FROM campaign as c LEFT JOIN plan as p ON c.plan_id = p.id WHERE c.id=%s",
                        [campaign_id])[0]
                    campaign_dict = dict()
                    campaign_dict['email'] = campaign.email
                    campaign_dict['user_id'] = str(campaign.user_id) if campaign.user_id else ""
                    campaign_dict['plan_name'] = campaign.plan_name
                    campaign_dict['plan_amount_per_month'] = campaign.plan_charge_per_month
                    campaign_dict['next_invoice_date'] = campaign.next_invoice_date.strftime(
                        "%d %b %Y") if campaign.next_invoice_date else "-"
                    campaign_dict['status'] = campaign.campaign_status
                    campaign_dict['domain_type'] = campaign.updated_domain_type
                    campaign_dict['is_cancelled'] = campaign.is_cancelled
                    return JsonResponse({'campaign': json.dumps(campaign_dict)})
            except CampaignDoesNotExist as cdne:
                log.error(msg=cdne.message)
                messages.error(request, message=cdne.message)
                return JsonResponse({'error_message': cdne.message, 'error_tag': cdne.item.get('error_tag'),
                                     'error': cdne.item.get('error')})
            except ActionRequiredException as are:
                log.error(msg=are.message)
                messages.error(request, message=are.message)
                if are.item:
                    return JsonResponse({'error_message': are.message, 'error_tag': are.item.get('error_tag')})
                return JsonResponse({'error_message': are.message, 'error_tag': are.item.get('error_tag'),
                                     'error': are.item.get('error')})
            except Exception as e:
                message = "Something went wrong while updating App Password."
                log.error(msg=f"{message} and Error: {e.args}")
                return JsonResponse(data={'error_message': message, 'error': e.args, 'error_tag': "404"})


class CampaignListWithSearchView(LoginRequiredMixin, View):
    """
    Renders Campaign List Tbody with Context using AJAX Post Method
    """

    def post(self, request):
        """
        AJAX post Method to renders Campaign List Tbody with Filtered Campaign List as Context
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            log.info(msg="Entered into Filtered Campaign List Campaign AJAX Post Method for Join Team Flow.")
            try:
                search_value = json.load(request).get('search_value').lower()
                master_user_id = request.user.id
                campaigns = Campaign.objects.raw(
                    f"SELECT c.id, c.email, c.email_service_provider, c.domain_type, c.next_invoice_date, p.name, CASE c.domain_type WHEN 'custom' THEN 'Custom' WHEN 'new_domain' THEN 'Warmup New Email' WHEN 'repair' THEN 'Repair Reputation' WHEN 'maintain_deliverability' THEN 'Maintain Deliverability' END AS updated_domain_type, CASE WHEN p.name IS NOT NULL THEN p.name ELSE 'Payment Required' END AS plan_name, CASE WHEN c.is_stopped IS TRUE THEN 'Paused' ELSE 'Running' END AS campaign_status, CASE WHEN c.master_user_id=c.user_id THEN 'self' ELSE 'invited' END AS campaign_owner FROM campaign as c LEFT JOIN plan as p ON c.plan_id = p.id WHERE master_user_id=%s and (LOWER(c.email) LIKE %s OR LOWER(p.name) LIKE %s) ORDER BY c.email",
                    [master_user_id, f"%{search_value}%", f"%{search_value}%"])
                context = {
                    'campaigns': campaigns
                }
                return render(request, 'campaigns/campaign_list_tbody.html', context=context)
            except Exception as e:
                print(e)


class CancelSubscriptionView(LoginRequiredMixin, View):
    """
    Cancel Subscription by Campaign Email
    """

    def post(self, request):
        """
        Cancel Subscription and Update Campaign by Post Ajax Method
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            try:
                warmup_email = json.load(request).get('warmup_email')
                subscription_id = PaymentAppServices().get_latest_payment_by_warmup_email(
                    warmup_email=warmup_email).stripe_subscription.get('id')
                cancel_subscription = StripeAppServices().cancel_subscription_by_stripe_subscription_id(
                    subscription_id=subscription_id)
                if cancel_subscription.get('cancellation_details').get("reason"):
                    campaign_instance = CampaignAppServices().get_campaign_by_email(email=warmup_email)
                    campaign_instance.is_cancelled = True
                    campaign_instance.save()
                    # TODO : Update Campaign using Celery Scheduler at period end
                    message = f"{warmup_email} Subscription Cancelled successfully."
                    messages.success(request, message=message)
                    return JsonResponse({'success': True})
                else:
                    raise StripeSubscriptionException(
                        message="Something went Wrong in Stripe while cancelling a Subscription.")
            except CampaignDoesNotExist as cdne:
                log.error(msg=cdne.message)
                messages.error(request, message=cdne.message)
                return JsonResponse({'error_message': cdne.message, 'error_tag': cdne.item.get('error_tag'),
                                     'error': cdne.item.get('error')})
            except PaymentDoesNotExist as pdne:
                log.error(msg=pdne.message)
                messages.error(request, message=pdne.message)
                return JsonResponse({'error_message': pdne.message, 'error_tag': pdne.item.get('error_tag'),
                                     'error': pdne.item.get('error')})
            except ActionRequiredException as apr:
                log.error(msg=apr.message)
                messages.error(request, message=apr.message)
                return JsonResponse({'error_message': apr.message, 'error_tag': apr.item.get('error_tag'),
                                     'error': apr.item.get('error')})
            except StripeSubscriptionException as sse:
                log.error(msg=sse.message)
                messages.error(request, message=sse.message)
                return JsonResponse({'error_message': sse.message, 'error_tag': sse.item.get('error_tag'),
                                     'error': sse.item.get('error')})
            except Exception as e:
                message = "Something went wrong while Canceling subscription."
                log.error(msg=f"{message} and Error: {e.args}")
                messages.error(request, message=message)
                return JsonResponse(data={'error_message': message, 'error': e.args, 'error_tag': "404"})


class SendInvitationLinkView(LoginRequiredMixin, View):
    """
    Send Invitation Link Manually
    """

    def get(self, request, hidden_text):
        """
        Send Invitation Link Manually by Master User
        """
        try:
            user = request.user
            warmup_email = hidden_text.split("break_point")[0]
            comes_from = hidden_text.split("break_point")[1]
            if user.is_master_user:
                CampaignAppServices().create_invitation_link_and_send_mail_to_invitee(master_user_id=user.id,
                                                                                      warmup_email=warmup_email,
                                                                                      current_site=get_current_site(
                                                                                          request))
                message = f"Invitation mail sent successfully to {warmup_email}."
                messages.success(request, message=message)
                if comes_from == "member_list":
                    return redirect("profiles:member_list")
                elif comes_from == "campaign_list":
                    return redirect("campaigns:list")
                else:
                    return redirect("users:404")
            else:
                raise StripeSubscriptionException(
                    message="Something went Wrong in Stripe while cancelling a Subscription.")
        except CampaignDoesNotExist as cdne:
            log.error(msg=cdne.message)
            messages.error(request, message=cdne.message)
            return JsonResponse({'error_message': cdne.message, 'error_tag': cdne.item.get('error_tag'),
                                 'error': cdne.item.get('error')})


class CeleryMailView(View):
    def get(self, request):
        # Initialize Thread and Template Repo
        thread_repo = ThreadServices().get_thread_repo()
        template_repo = TemplateServices().get_template_repo()

        # Start Time Counter
        time_counter.delay()

        # Get All Campaign Which is Going to be Warmup
        all_campaigns = CampaignAppServices().list_campaigns().filter(is_stopped=False, app_password__isnull=False,
                                                                      action_required=CampaignActionRequiredChoices.NONE)
        for campaign in all_campaigns:
            # Get Encrypted App Password and Checking App Password, Plan ID, Email Service Provider are available
            app_password = SecretEncryption().decrypt_secret_string(encrypted_string=campaign.app_password)
            if campaign.plan_id and app_password and campaign.email_service_provider in ['gmail', 'outlook']:
                # Get Total mails to be sent and update it by step up
                total_mails_to_send = campaign.mails_to_be_sent
                if int(campaign.mails_to_be_sent) < int(campaign.max_email_per_day):
                    total_mails_to_send = int(campaign.mails_to_be_sent) + int(
                        campaign.email_step_up)
                    campaign.mails_to_be_sent = total_mails_to_send
                    campaign.save()

                domain_list = CampaignAppServices().list_domain_lists().filter(is_active=True)
                receivers_data_dict_list = [email for email in
                                            domain_list.values('email', 'app_password', 'email_service_provider')]

                thread_subquery = thread_repo.filter(template_id=OuterRef("id")).order_by("-thread_ordering_number")

                templates_list = list(template_repo.filter(warmup_email=campaign.email).annotate(
                    total_threads=Subquery(thread_subquery.values("thread_ordering_number")[:1])))
                if not templates_list:
                    templates_list = list(template_repo.filter(is_general=True).annotate(
                        total_threads=Subquery(thread_subquery.values("thread_ordering_number")[:1])))
                random_templates = random.sample(templates_list, len(templates_list))

                total_threads = 0
                max_threads_in_template = 0
                finalized_templates = []

                template_number = 0
                while True:
                    if total_threads < (2 * total_mails_to_send) and total_threads - (2 * total_mails_to_send) <= -2:
                        finalized_templates.append(random_templates[template_number])
                        template_number += 1
                        if template_number == len(random_templates):
                            template_number = 0
                        if random_templates[template_number].total_threads > max_threads_in_template:
                            max_threads_in_template = random_templates[template_number].total_threads
                        total_threads += random_templates[template_number].total_threads
                    else:
                        break

                if len(receivers_data_dict_list) < len(finalized_templates):
                    finalized_templates = finalized_templates[:len(receivers_data_dict_list)]
                finalized_receivers_dict = random.sample(receivers_data_dict_list, len(finalized_templates))

                template_fixture = list()
                for index in range(len(finalized_templates)):
                    data_dict = dict()
                    # Receivers
                    data_dict["receiver_email"] = finalized_receivers_dict[index].get('email')
                    data_dict["app_password"] = finalized_receivers_dict[index].get('app_password')
                    data_dict["email_provider"] = finalized_receivers_dict[index].get('email_service_provider')
                    data_dict["template_name"] = finalized_templates[index].name
                    data_dict["template_subject"] = finalized_templates[index].subject

                    threads = (
                        thread_repo.filter(template_id=finalized_templates[index].id)
                        .order_by("thread_ordering_number")
                        .values_list("body", flat=True)
                    )
                    data_dict["thread_list"] = list(threads)
                    data_dict["thread_count"] = len(data_dict["thread_list"])
                    template_fixture.append(data_dict)

                # Email Data
                sender_data_dict = dict()
                sender_data_dict['email'] = campaign.email
                sender_data_dict['email_service_provider'] = campaign.email_service_provider
                sender_data_dict['app_password'] = app_password

                for template in template_fixture:
                    max_time_to_complete_all_process = int(getattr(settings, "MAX_TIME_TO_COMPLETE_ALGORITHM", "72000"))
                    time_to_be_sent_one_mail = int(max_time_to_complete_all_process / max_threads_in_template * 0.98)
                    delay_for_sending_mail = random.randint(3, time_to_be_sent_one_mail)
                    message_id = 0
                    send_email_task_schedular.apply_async(
                        (delay_for_sending_mail, "sender", sender_data_dict, template.get('thread_list'), 0,
                         template.get('template_subject'), time_to_be_sent_one_mail, template.get('receiver_email'),
                         template.get('app_password'), template.get('email_provider'), message_id, total_mails_to_send),
                        countdown=delay_for_sending_mail,
                    )
        return HttpResponse("All Campaign Algorithm Completed Successfully.")


class CeleryMailDataView(View):
    def get(self, request):
        file_date = datetime.datetime.now().strftime("%Y-%m-%d")
        df = CampaignAppServices().read_record_file_to_list_of_dict(file_date=file_date)

        df.to_excel(f"utils/embermail_data_excels/{file_date}.xlsx",
                    index=False)
        return HttpResponse("Success")


class CampaignReportView(View):
    def get(self, request):
        # CampaignAppServices().create_campaign_reports_by_log_records()
        create_campaign_reports_by_log_records.delay()
        return HttpResponse("Campaign Report Success")

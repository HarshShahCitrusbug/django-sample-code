import datetime
import json
import logging

from django.shortcuts import render
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.generic import View
from django.contrib.auth import logout, login
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site

from embermail.application.campaigns.services import CampaignAppServices
from utils.utility_services import UtilityServices
from embermail.application.users.services import UserAppServices
from embermail.infrastructure.logger.models import AttributeLogger
from utils.data_manipulation.type_conversion import decode_by_base64
from utils.django.exceptions import UserDoesNotExist, InvalidCredentialsException, ValidationException, \
    UserAlreadyExist, UserRegistrationException, UserDoesNotVerified, ForgotPasswordLinkExpired, \
    ForgotPasswordException, VisitedUserCreationException, SendgridEmailException, InquiryException

log = AttributeLogger(logging.getLogger(__name__))


@login_required
def home(request):
    """
    View - Home/Dashboard
    """
    log.info(msg="Entered into Home Page.")
    return render(request, 'users/home.html')


class OnboardingView(View):
    """
    View - Collect Email for Login/Signup
    """

    def get(self, request):
        """
        Render Onboarding Page with List of used emails and Template Selection(Login/Signup) basis on email exist
        """
        if not request.user.is_authenticated:
            try:
                invitation_link = request.GET.get('token')
                if invitation_link:
                    log.info(msg="Entered into Onboarding View Page for Invitation.")
                    invitation_link_token = decode_by_base64(string=invitation_link).split("break_point")
                    master_user_id = invitation_link_token[0]
                    # Deleting master_user_id_for_join_flow from Django Session
                    if 'master_user_id_for_join_team_flow' in request.session:
                        del request.session["master_user_id_for_join_team_flow"]
                        log.info(
                            msg="master_user_id_for_join_team_flow deleted from Django Session from OnboardingView Get Method.")
                    request.session['master_user_id_for_join_team_flow'] = master_user_id
                    warmup_email = invitation_link_token[1]
                    expiration_time = invitation_link_token[2]
                    if expiration_time and warmup_email:
                        expiration_time_datetime_formatted = datetime.datetime.strptime(expiration_time,
                                                                                        "%d-%m-%y %H:%M:%S")
                        if expiration_time_datetime_formatted <= datetime.datetime.now():
                            messages.error(request, "Invitation link is expired. Please, Contact your master user.")
                            return render(request, 'users/onboarding.html')

                        campaign_exist = CampaignAppServices().check_campaign_exists_by_email(email=warmup_email)
                        if not campaign_exist:
                            raise Exception
                        return render(request, 'users/onboarding.html',
                                      context={'email': warmup_email, 'master_user_id': master_user_id})
                    raise Exception
            except Exception as e:
                log.error(
                    msg=f"Something Went wrong while Onboarding for Invitation and Redirecting to 404 Page. Error: {e.args}")
                return render(request, '404.html')  # TODO : Return 404 Error Page

            log.info(msg="Entered into Onboarding View Page.")
            ip_address = UtilityServices().get_ip_address(request=request)
            visited_user_email_list = list(
                UserAppServices().list_visited_user_by_ip_address(ip_address=ip_address).values())
            log.info(msg="Got successfully visited user email list.")
            onboarding_selected = request.GET.get('onboarding_selected')
            email = request.GET.get('email')
            if onboarding_selected is not None:
                if onboarding_selected == 'login':
                    log.info(msg="Rendering Onboarding Login Page.")
                    return render(request, 'users/onboarding_login.html')
                else:
                    log.info(msg="Rendering Onboarding Signup Page.")
                    return render(request, 'users/onboarding_signup.html', context={'email': email})
            context = {'visited_user_emails': visited_user_email_list}
            log.info(msg="Rending Onboarding Page with visited_user_emails context.")
            return render(request, 'users/onboarding.html', context=context)
        log.info(msg=f"User({request.user.email}) has Already Authenticated and is Redirecting to Home Page.")
        return redirect('users:home')

    def post(self, request):
        """
        Checks Email is Exists and Creates VisitedUser
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            log.info(msg="Entered into Onboarding AJAX Post Method.")
            try:
                data = json.load(request)
                email = data.get('email')
                email_exists = UserAppServices().check_user_email_exists(email=email)
                ip_address = UtilityServices().get_ip_address(request)
                UserAppServices().create_visited_user(ip_address=ip_address, email=email)
                log.info(msg="User created using visited user Email and IPAddress and returns exist: True")
                return JsonResponse({"exist": email_exists})
            except VisitedUserCreationException as vuce:
                log.error(msg=vuce.message)
                return JsonResponse(
                    data={'error_message': vuce.message, 'error_tag': vuce.item.get('error_tag'), 'error': vuce.args})
            except Exception as e:
                message = "Something went wrong while Onboarding"
                log.error(msg=message)
                return JsonResponse(data={'error_message': message, 'error': e.args})
        log.error(msg="Something Went wrong while Post Method of Onboarding and Redirecting to 404 Page.")
        return render(request, '404.html')  # TODO : Return 404 Error Page


class OnboardingSignupView(View):
    """
    View - User Registration/Signup
    """

    def post(self, request):
        """
        Creates User if Not Exist and Send a Mail for Verification
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            log.info(msg="Entered into Onboarding Signup AJAX Post Method.")
            try:
                data = json.load(request)
                data['current_site'] = get_current_site(request)
                signup_flow_type = data.get('signup_flow', None)

                if signup_flow_type == "join_team":
                    master_user_id_for_joining_flow = request.session.get('master_user_id_for_join_team_flow')
                    data['master_user_id_for_joining_flow'] = master_user_id_for_joining_flow

                user = UserAppServices().create_user_from_dict(data=data)

                if signup_flow_type == "join_team":
                    log.info(msg=f"User({user.email}) created successfully from invitation link using ajax data.")
                    user = UserAppServices().manually_authenticate_and_login_user(email=user.email,
                                                                                  password=data.get('password'))
                    if user:
                        login(request, user)
                        log.info(msg=f"User({user.email}) logged in successfully after registration of joining user.")
                        if 'master_user_id_for_join_team_flow' in request.session:
                            del request.session["master_user_id_for_join_team_flow"]
                            log.info(
                                msg="master_user_id_for_join_team_flow deleted from Django Session from OnboardingSignupView.")
                        message = f"User({user.email}) logged in successfully"
                        messages.success(request, message)
                        return JsonResponse({"logged_in": True})
                    log.info(msg="User is not Authenticated.")

                message = "Registration Completed Successfully. Please Verify your Email using verification link sent in registered email."
                messages.success(request, message)
                log.info(msg=f"User({user.email}) created successfully from ajax data.")
                return JsonResponse({"registered": True})

            except ValidationException as ve:
                log.error(msg=ve.message)
                data = {'error_message': ve.message, 'error_tag': ve.item.get('error_tag'), 'error': ve.args}
                print(data)
                return JsonResponse(
                    data={'error_message': ve.message, 'error_tag': ve.item.get('error_tag'), 'error': ve.args})
            except UserAlreadyExist as uae:
                log.error(msg=uae.message)
                return JsonResponse(
                    data={'error_message': uae.message, 'error_tag': uae.item.get('error_tag'), 'error': uae.args})
            except SendgridEmailException as sgee:
                log.error(msg=sgee.message)
                messages.error(request, sgee.message)
                return JsonResponse(data={'registered': True})
            except UserRegistrationException as ure:
                log.error(msg=ure.message)
                return JsonResponse(
                    data={'error_message': ure.message, 'error_tag': ure.item.get('error_tag'), 'error': ure.args})
            except Exception as e:
                message = "Something went wrong while Onboarding Signup."
                log.error(msg=f"{message} & Error: {e.args}")
                return JsonResponse(data={'error_message': message, 'error': e.args})
        log.error(msg="Something went wrong while Onboarding Signup AJAX Post method and Redirecting to 404 page.")
        return render(request, '404.html')  # TODO : Return 404 Error Page


class OnboardingLoginView(View):
    """
    View - User Login View
    """

    def post(self, request):
        """
        Authenticate a User if is_verified is True
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            log.info(msg="Entered into Onboarding Login AJAX Post Method.")
            data = json.load(request)
            email = data.get('email')
            password = data.get('password')
            try:
                user = UserAppServices().manually_authenticate_and_login_user(email=email, password=password)
                if user:
                    login(request, user)
                    redirect_path = "/campaigns/list"
                    if CampaignAppServices().check_campaign_exists_by_master_user(
                            master_user_id=user.id) or CampaignAppServices().check_campaign_exists_by_email(
                        email=user.email):
                        redirect_path = "/home"
                    log.info(msg=f"User({user.email}) logged in successfully.")
                    return JsonResponse({"logged_in": True, "redirect": redirect_path})
                log.info(msg="User is not Authenticated.")
            except UserDoesNotVerified as udnv:
                log.error(msg=udnv.message)
                return JsonResponse(
                    {"error_message": udnv.message, 'error_tag': udnv.item.get('error_tag'), 'error': udnv.args})
            except UserDoesNotExist as usne:
                log.error(msg=f"{usne.message} and Rendering to Onboarding Signup Page.")
                return render(request, 'users/onboarding_signup.html')
            except InvalidCredentialsException as ice:
                log.error(msg=ice.message)
                return JsonResponse(
                    {"error_message": ice.message, 'error_tag': ice.item.get('error_tag'), 'error': ice.args})
        log.error(msg="Something went wrong while login and Rendering to 404 Page.")
        return render(request, '404.html')  # TODO : Return 404 Error Page


def logout_view(request):
    """
    Logout  and Redirect to Onboarding Page
    """
    try:
        email = request.user.email
        logout(request)
        log.info(msg=f"User({email}) logged out successfully and Redirecting to Onboarding Page.")
        return redirect('users:onboarding')
    except Exception as e:
        return render(request, '404.html')


def user_email_verification(request, encoded_user_id: str):
    """
    Verify User's email by Verification Link sent in Registered Email
    """
    log.info(msg="Entered into User email verification")
    try:
        user = UserAppServices().verify_user_by_verification_link(encoded_user_id=encoded_user_id)
        log.info(msg=f"User({user.email}) is verified successfully and Redirecting to Onboarding Login Page.")
        messages.success(request, message="Email Verified Successfully. You can login here.")
        return redirect("users:onboarding")
    except Exception as e:
        log.error(msg="Something went wrong while verifying user email and Rendering to 404 Page.")
        messages.error(request, message="Please, try after some time.")
        return render(request, '404.html')  # TODO : Return 404 Error Page


class PasswordResetView(View):
    def get(self, request):
        log.info(msg="Entered into password reset view.")
        return render(request, 'users/password_reset.html')

    def post(self, request):
        """
        AJAX - Post Method of PasswordResetView
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            log.info(msg="Entered into Password Reset View's AJAX Post Method.")
            try:
                data = json.load(request)
                data['current_site'] = get_current_site(request)
                UserAppServices().create_forgot_password_by_dict(data=data)
                message = f"Password reset instruction sent to {data.get('email', '')}."
                messages.success(request, message)
                log.info(msg=f"{message} and returns email_exists: True")
                return JsonResponse({"email_exists": True})
            except UserDoesNotExist as usne:
                log.error(msg=usne.message)
                return JsonResponse({"email_exists": False})
            except SendgridEmailException as sgee:
                log.error(msg=sgee.message)
                return JsonResponse({"error_message": sgee.message, 'error': sgee.args})
            except Exception as e:
                message = "Something went wrong while PasswordReset"
                log.error(msg=message)
                return JsonResponse({'error_message': message, 'error': e.args})
        log.error(msg="Something went wrong while Password Reset and redirecting to 404 page.")
        return render(request, '404.html')  # TODO : Return 404 Error Page


class PasswordResetConfirmView(View):
    def get(self, request):
        """
        Verify Token and Check Expiry date of token
        """
        log.info(msg="Entered into password reset confirm view.")
        try:
            encoded_token = request.GET.get('token')
            UserAppServices().verify_forgot_password_token(encoded_token=encoded_token)
            log.info(msg="Verified Forgot Password Token successfully and rendering to password reset confirm page.")
            return render(request, 'users/password_reset_confirm.html')
        except ForgotPasswordLinkExpired:
            message = "Forgot Password Link is Expired. Please, Try Again."
            messages.warning(request, message)
            log.error(msg=f"{message} and redirecting to Onboarding page.")
            return redirect('users:onboarding')
        except Exception as e:
            log.error(msg=f"Something went wrong while verifying forgot password link and Error: {e.args}.")
            return render(request, '404.html')  # TODO : Return 404 Error Page

    def post(self, request):
        """
        AJAX - Post Method of PasswordConfirmView
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            log.info(msg="Entered into Password Reset Confirm View's AJAX Post Method.")
            try:
                data_dict = json.load(request)
                data_dict['current_site'] = get_current_site(request)
                UserAppServices().set_new_password_for_forgot_password(data=data_dict)
                message = "Password reset successfully."
                messages.success(request, message)
                log.info(msg=f"{message} and returns reset_successful: True.")
                return JsonResponse({"reset_successful": True})
            except ValidationException as ve:
                log.error(msg=ve.message)
                return JsonResponse({"error_message": ve.message, 'error_tag': ve.item.get('error_tag')})
            except SendgridEmailException as sgee:
                log.error(msg=sgee.message)
                return JsonResponse({"reset_successful": True})
            except ForgotPasswordException as fpe:
                log.error(msg=fpe.message)
                return JsonResponse(
                    {"error_message": fpe.message, 'error_tag': fpe.item.get('error_tag'), 'error': fpe.args})
            except Exception as e:
                log.error(msg=f"Something went wrong while setting up new password and Error: {e.args}.")
                return render(request, '404.html')  # TODO : Return 404 Error Page
        log.error(msg=f"Something went wrong while setting up new password and rendering to 404 page.")
        return render(request, '404.html')  # TODO : Return 404 Error Page


def error_404_page_view(request):
    return render(request, "404.html")


class ContactUsView(View):
    """
    Contact Page Rendering and Saving Contact Form with Message
    """

    def get(self, request):
        """
        Rendering Contact Page
        """
        return render(request, 'users/contact.html')

    def post(self, request):
        """
        AJAX - Post Method for Saving Contact Us Form
        """
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            log.info(msg="Entered into Contact Us View's AJAX Post Method.")
            try:
                data_dict = json.load(request)
                UserAppServices().create_inquiry_by_contact_us_form_data(data=data_dict)
                message = "Message Submitted Successfully."
                messages.success(request, message)
                log.info(msg=f"{message} and returns submitted: True.")
                return JsonResponse({"submitted": True})
            except InquiryException as ie:
                log.error(msg=ie.message)
                return JsonResponse(
                    {"error_message": ie.message, 'error_tag': ie.item.get('error_tag'), 'error': ie.item.get('error')})
            except Exception as e:
                log.error(msg=f"Something went wrong while creating inquiry and Error: {e.args}.")
                return render(request, '404.html')
        log.error(msg=f"Something went wrong while creating inquiry and rendering to 404 page.")
        return render(request, '404.html')

import json
import uuid

from django.views import View
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin

from embermail.application.campaigns.services import CampaignAppServices
from embermail.application.templates.services import TemplateAppServices
from utils.django.exceptions import TemplateDoesNotExist, ThreadDoesNotExist, TemplateThreadAccessDenied, \
    TemplateAlreadyExist, CampaignDoesNotExist


class TemplateListView(LoginRequiredMixin, View):
    """
    List All Templates
    """

    def get(self, request):
        try:
            warmup_email_list = list()
            warmup_email = None
            selected_email = request.GET.get('selected_warmup', None)
            if request.user.is_master_user:
                warmup_email_list = CampaignAppServices().list_campaigns_by_master_user_id(
                    master_user_id=request.user.id).order_by('email').values("email", "email_service_provider",
                                                                             "user_id", "id")
                if warmup_email_list:
                    if selected_email:
                        campaign_id = selected_email
                        campaign_instance = CampaignAppServices().get_campaign_by_id(id=uuid.UUID(campaign_id))
                        warmup_email = selected_email = campaign_instance.email
                        if not (campaign_instance.user_id == request.user.id or campaign_instance.master_user_id == request.user.id):
                            raise TemplateThreadAccessDenied(message="Access Denied.", item={})
                    else:
                        warmup_email = warmup_email_list[0].get('email')
            else:
                warmup_email = request.user.email
            template_list = TemplateAppServices().list_templates().filter(
                Q(warmup_email__isnull=True) | Q(warmup_email=warmup_email)).order_by("-created_at").distinct()
            context = {
                'template_list': template_list,
                'warmup_email_list': warmup_email_list,
                'selected_email': selected_email
            }
            return render(request, "templates/template_list.html", context=context)
        except TemplateThreadAccessDenied as ttad:
            messages.error(request, message=ttad.message)
            return redirect("templates:template_list")
        except Exception as e:
            return render(request, '404.html')  # TODO: Add 404 Page


class AddNewTemplateAJAXView(LoginRequiredMixin, View):
    """
    AJAX for Add New Template
    """

    def post(self, request):
        # AJAX post Method
        try:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                template_data_dict: dict = json.load(request)
                user = request.user
                template_data_dict['user_id'] = user.id
                template_data_dict['master_user_id'] = user.users_master_id
                if user.is_master_user:
                    template_data_dict['warmup_email'] = template_data_dict.get('selected_email')
                    CampaignAppServices().check_campaign_owner_by_email(login_user_id=user.id,
                                                                        email=template_data_dict.get('warmup_email'))
                else:
                    template_data_dict['warmup_email'] = user.email
                TemplateAppServices().create_template_by_name_and_subject(template_data_dict=template_data_dict)
                return JsonResponse({'redirect': "/templates/list/"})
            message = "Something went wrong while adding new template."
            messages.warning(request, message)
            return JsonResponse({'error': "Something Went wrong in AJAX while adding new template.",
                                 'redirect': "/templates/list/"})
        except CampaignDoesNotExist as cdne:
            return JsonResponse(
                {'error_message': "To Access Templates Functionality, Please Start Campaign.",
                 'error': cdne.item.get('error')})
        except TemplateAlreadyExist as tae:
            return JsonResponse(
                {'error_message': tae.message, 'error': tae.item.get('error')})
        except Exception as e:
            message = "Something went wrong while adding new template."
            messages.warning(request, message)
            return JsonResponse({'redirect': "/templates/list/"})


class UpdateTemplateStatusAJAXView(LoginRequiredMixin, View):
    """
    AJAX for Changing Template's Status (Active/Inactive)
    """

    def post(self, request):
        try:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                template_data_dict = json.load(request)
                template_id: str = template_data_dict.get('template_id')

                user = request.user
                warmup_email = user.email
                if user.is_master_user:
                    warmup_email = template_data_dict.get('selected_email')
                    CampaignAppServices().check_campaign_owner_by_email(login_user_id=user.id, email=warmup_email)
                TemplateAppServices().update_status_of_template_is_selected(template_id=template_id,
                                                                            warmup_email=warmup_email,
                                                                            user_id=request.user.id,
                                                                            master_user_id=request.user.users_master_id)
                messages.success(request, "Active-Inactive Status Updated.")
                return JsonResponse({'redirect': "/templates/list/"})
            message = "Something went wrong while updating template status."
            messages.error(request, message)
            return JsonResponse({'error': "Something Went wrong in AJAX while updating template status.",
                                 'redirect': "/templates/list/"})
        except CampaignDoesNotExist as cdne:
            message = "To Access Templates Functionality, Please Start Campaign."
            messages.error(request, message)
            return JsonResponse(
                {'redirect': "/templates/list/", 'error': cdne.item.get('error')})
        except TemplateThreadAccessDenied as ttad:
            messages.error(request, ttad.message)
            return JsonResponse(
                {'redirect': "/templates/list/", 'error': ttad.item.get('error')})
        except TemplateDoesNotExist as tdne:
            messages.error(request, tdne.message)
            return JsonResponse(
                {'redirect': "/templates/list/", 'error': tdne.item.get('error')})
        except Exception as e:
            message = "Something went wrong while updating template status."
            messages.warning(request, message)
            return JsonResponse({'redirect': "/templates/list/"})


class UpdateTemplateAJAXView(LoginRequiredMixin, View):
    """
    AJAX for updating Template's Name and Subject
    """

    def post(self, request):
        try:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                template_data_dict: dict = json.load(request)
                user = request.user
                template_data_dict['user_id'] = user.id
                template_data_dict['master_user_id'] = user.users_master_id
                template_data_dict['warmup_email'] = user.email
                if user.is_master_user:
                    template_data_dict['warmup_email'] = template_data_dict.pop('selected_email')
                    CampaignAppServices().check_campaign_owner_by_email(login_user_id=user.id,
                                                                        email=template_data_dict.get('warmup_email'))
                TemplateAppServices().update_template_by_name_and_subject(template_data_dict=template_data_dict)
                messages.success(request, "Template Data Updated Successfully.")
                return JsonResponse({'redirect': "/templates/list/"})
            message = "Something went wrong while updating template."
            messages.warning(request, message)
            return JsonResponse({'error': "Something Went wrong in AJAX while updating template.",
                                 'redirect': "/templates/list/"})
        except CampaignDoesNotExist as cdne:
            message = "To Access Templates Functionality, Please Start Campaign."
            messages.error(request, message)
            return JsonResponse(
                {'redirect': "/templates/list/", 'error': cdne.item.get('error')})
        except TemplateThreadAccessDenied as ttad:
            messages.error(request, ttad.message)
            return JsonResponse(
                {'redirect': "/templates/list/", 'error': ttad.item.get('error')})
        except TemplateDoesNotExist as tdne:
            messages.error(request, tdne.message)
            return JsonResponse(
                {'redirect': "/templates/list/", 'error': tdne.item.get('error')})
        except TemplateAlreadyExist as tae:
            return JsonResponse(
                {'error_message': tae.message, 'error': tae.item.get('error')})
        except Exception as e:
            message = "Something went wrong while updating template."
            messages.warning(request, message)
            return JsonResponse({'redirect': "/templates/list/"})


class DeleteTemplateAJAXView(LoginRequiredMixin, View):
    """
    AJAX for Deleting Template
    """

    def post(self, request):
        try:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                template_data_dict = json.load(request)
                template_id = template_data_dict.get('template_id')
                user = request.user
                warmup_email = user.email
                if user.is_master_user:
                    warmup_email = template_data_dict.get('selected_email')
                    CampaignAppServices().check_campaign_owner_by_email(login_user_id=user.id,
                                                                        email=warmup_email)
                TemplateAppServices().delete_template_by_template_id(template_id=template_id, warmup_email=warmup_email,
                                                                     user_id=user.id,
                                                                     master_user_id=user.users_master_id)
                messages.success(request, "Template Deleted Successfully.")
                return JsonResponse({'redirect': "/templates/list/"})

            message = "Something went wrong while deleting template."
            messages.error(request, message)
            return JsonResponse({'error': "Something Went wrong in AJAX while deleting template.",
                                 'redirect': "/templates/list/"})
        except CampaignDoesNotExist as cdne:
            message = "To Access Templates Functionality, Please Start Campaign."
            messages.error(request, message)
            return JsonResponse(
                {'redirect': "/templates/list/", 'error': cdne.item.get('error')})
        except TemplateThreadAccessDenied as ttad:
            messages.error(request, ttad.message)
            return JsonResponse(
                {'redirect': "/templates/list/", 'error': ttad.item.get('error')})
        except TemplateDoesNotExist as tdne:
            messages.error(request, tdne.message)
            return JsonResponse(
                {'redirect': "/templates/list/", 'error': tdne.item.get('error')})

        except Exception as e:
            message = "Something went wrong while deleting template."
            messages.warning(request, message)
            return JsonResponse({'redirect': "/templates/list/"})


class AddDefaultTemplateAJAXView(LoginRequiredMixin, View):
    """
    AJAX for Adding Default Templates to User Templates
    """

    def post(self, request):
        try:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                template_data_dict = json.load(request)
                template_id = template_data_dict.get('template_id')
                user = request.user
                warmup_email = user.email
                master_user_id = user.users_master_id
                if user.is_master_user:
                    warmup_email = template_data_dict.get('selected_email')
                    master_user_id = user.id
                    CampaignAppServices().check_campaign_owner_by_email(login_user_id=user.id, email=warmup_email)
                created = TemplateAppServices().add_default_template_to_user_templates(default_template_id=template_id,
                                                                                       warmup_email=warmup_email,
                                                                                       user_id=request.user.id,
                                                                                       master_user_id=master_user_id)
                if created:
                    messages.success(request, "Default Template Added Successfully.")
                    return JsonResponse({'redirect': "/templates/list/"})
                messages.error(request, "Default Template Already Added.")
                return JsonResponse({'redirect': "/templates/list/"})
            message = "Something went wrong while adding default template."
            messages.warning(request, message)
            return JsonResponse({'error': "Something Went wrong in AJAX while adding default template.",
                                 'redirect': "/templates/list/"})
        except CampaignDoesNotExist as cdne:
            message = "To Access Templates Functionality, Please Start Campaign."
            messages.error(request, message)
            return JsonResponse({'redirect': "/templates/list/", 'error': cdne.item.get('error')})
        except TemplateDoesNotExist as tdne:
            messages.error(request, tdne.message)
            return JsonResponse(
                {'redirect': "/templates/list/", 'error': tdne.item.get('error')})
        except Exception as e:
            message = "Something went wrong while adding default template."
            messages.warning(request, message)
            return JsonResponse({'redirect': "/templates/list/"})


# =========================================================================================================
# THREAD VIEWS
# =========================================================================================================

class ThreadListView(LoginRequiredMixin, View):
    """
    Display all Threads of Selected Template
    """

    def get(self, request, template_id: uuid):
        try:
            template = TemplateAppServices().get_template_by_id(id=template_id)
            if template.user_id:
                if template.user_id != request.user.id:
                    messages.error(request, "Access Denied")
                    return redirect('templates:template_list')
            threads = TemplateAppServices().list_threads_by_template_id(template_id=template_id).order_by(
                'thread_ordering_number').values('id', 'template_id', 'body', 'thread_ordering_number')
            context = {
                'template': template,
                'threads': threads,
            }
            return render(request, 'templates/thread_list.html', context=context)

        except Exception:
            return render(request, '404.html')  # TODO: Add 404 Page


class AddNewThreadAJAXView(LoginRequiredMixin, View):
    """
    Adding New Thread Using AJAX
    """

    def post(self, request):
        try:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                thread_data_dict = json.load(request)
                template_id = thread_data_dict.get('template_id')
                TemplateAppServices().create_thread_by_template_id_and_body(
                    thread_data_dict=thread_data_dict)
                messages.success(request, "Thread Added Successfully.")
                return JsonResponse({'redirect': f"/templates/threads/list/{template_id}"})

            message = "Something went wrong while creating thread."
            messages.warning(request, message)
            return JsonResponse({'error': "Something Went wrong in AJAX while creating thread.",
                                 'redirect': "/templates/list/"})

        except Exception as e:
            message = "Something went wrong while creating thread."
            messages.warning(request, message)
            return JsonResponse({'redirect': "/templates/list/"})


class UpdateThreadAJAXView(LoginRequiredMixin, View):
    """
    Updating Thread Using AJAX
    """

    def post(self, request):
        try:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                thread_data_dict = json.load(request)
                thread_data_dict['user_id'] = request.user.id
                thread_instance = TemplateAppServices().update_thread_by_body(thread_data_dict=thread_data_dict)
                template_id = thread_instance.template_id
                messages.success(request, "Thread Updated Successfully.")
                return JsonResponse({'redirect': f"/templates/threads/list/{template_id}"})

            message = "Something went wrong while updating thread."
            messages.warning(request, message)
            return JsonResponse({'error': "Something Went wrong in AJAX while updating thread.",
                                 'redirect': f"/template/list/"})
        except TemplateThreadAccessDenied as ttad:
            messages.error(request, ttad.message)
            return JsonResponse(
                {'redirect': "/templates/list/", 'error': ttad.item.get('error')})
        except ThreadDoesNotExist as tdne:
            messages.error(request, tdne.message)
            return JsonResponse(
                {'redirect': "/templates/list/", 'error': tdne.item.get('error')})

        except Exception as e:
            message = "Something went wrong while updating thread."
            messages.warning(request, message)
            return JsonResponse({'redirect': "/templates/list/"})


class DeleteThreadAJAXView(LoginRequiredMixin, View):
    """
    Deleting Thread Using AJAX
    """

    def post(self, request):
        try:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                thread_data_dict = json.load(request)
                thread_data_dict['user_id'] = request.user.id
                template_id = thread_data_dict.get('template_id')
                TemplateAppServices().delete_thread_by_thread_id(thread_data_dict=thread_data_dict)
                messages.success(request, "Thread Deleted Successfully.")
                return JsonResponse({'redirect': f"/templates/threads/list/{template_id}"})

            message = "Something went wrong while deleting thread."
            messages.warning(request, message)
            return JsonResponse({'error': "Something Went wrong in AJAX while deleting thread.",
                                 'redirect': "/template/list/"})
        except TemplateThreadAccessDenied as ttad:
            messages.error(request, ttad.message)
            return JsonResponse(
                {'redirect': "/templates/list/", 'error': ttad.item.get('error')})
        except ThreadDoesNotExist as tdne:
            messages.error(request, tdne.message)
            return JsonResponse(
                {'redirect': "/templates/list/", 'error': tdne.item.get('error')})

        except Exception as e:
            message = "Something went wrong while deleting thread."
            messages.warning(request, message)
            return JsonResponse({'redirect': "/templates/list/"})

# class MyAuctionsListView(ListView):
#     """
#     My Auction List View
#     """

#     logger.info("My Auction Listing View")

#     model = SellProductImages

#     def get_template_names(self):
#         page = int(self.request.GET.get("page", 1))
#         if page == 1:
#             template_name = "frontend/subpages/my_auctions_list.html"
#         else:
#             template_name = "frontend/subpages/my_auctions_paginated_result.html"
#         return template_name

#     def get_context_data(self, args, *kwargs) -> dict:
#         context = super().get_context_data(**kwargs)

#         filters = {}
#         search_filter = []

#         search_query = self.request.GET.get("search", None)
#         sort_product_date = self.request.GET.get("within", None)
#         qry_product_condition = self.request.GET.get("product_condition", None)
#         qry_subcategory = self.request.GET.get("product_subcategory", [])

#         page = int(self.request.GET.get("page", 1))

#         utc_time = datetime.datetime.utcnow()
#         user_time_zone = self.request.user.time_zone
#         if user_time_zone.sign == "+":
#             user_current_date_time = utc_time + datetime.timedelta(
#                 hours=int(user_time_zone.hours), minutes=int(user_time_zone.minutes)
#             )
#         if user_time_zone.sign == "-":
#             user_current_date_time = utc_time - datetime.timedelta(
#                 hours=int(user_time_zone.hours), minutes=int(user_time_zone.minutes)
#             )

#         product_category = ProductCategory.objects.filter(parent_category=None)
#         product_conditions = Condition.objects.all()

#         qry_subcategory_updated = []
#         if len(qry_subcategory) > 0:
#             for category_id in qry_subcategory.split(","):
#                 if category_id != "":
#                     qry_subcategory_updated.append(int(category_id))
#             try:
#                 filters["product_category__id"] = qry_subcategory_updated[-1]
#             except Exception:
#                 logger.error(
#                     "There was an Error to get product category, then assign it to None"
#                 )
#                 filters["product_category__parent_category"] = None

#         if sort_product_date:
#             current_date = (
#                     datetime.datetime.now() + datetime.timedelta(days=(1))
#             ).date()
#             users_date = sort_product_by_day_month_year(sort_product_date)

#             filters["created_at__range"] = [users_date, current_date]

#         if qry_product_condition:
#             filters["product_condition__name__icontains"] = qry_product_condition

#         if search_query:
#             search_filter.append(
#                 Q(product_name__icontains=search_query)
#                 | Q(summary__icontains=search_query)
#                 | Q(product_upc_barcode__icontains=search_query)
#                 | Q(price__icontains=search_query)
#             )

#         result_list = (
#             SellProduct.objects.filter(
#                 user=self.request.user,
#                 *search_filter,
#                 **filters,
#                 product_type="is_auction",
#             )
#             .order_by("-created_at")
#             .distinct("created_at")
#         )
#         paginated_result_list = Paginator(result_list, 10)
#         latest_paginated_result_list = paginated_result_list.page(page)
#         latest_paginated_result_list_data = latest_paginated_result_list.object_list

#         total_bids = 0
#         if result_list:
#             bids = UserBids.objects.filter(sell_product=result_list[0]).order_by("-id")
#             total_bids = len(bids)

#         if len(result_list) > 10:
#             require_pagination = True
#         else:
#             require_pagination = False

#         if latest_paginated_result_list.has_next() is True:
#             require_pagination = True
#         else:
#             require_pagination = False

#         context = {
#             "my_auctions": latest_paginated_result_list_data,
#             "total_bids": total_bids,
#             "user_current_date_time": user_current_date_time,
#             "require_pagination": require_pagination,
#             "product_category": product_category,
#             "product_conditions": product_conditions,
#             "sort_product_date": sort_product_date,
#             "qry_subcategory": qry_subcategory_updated,
#         }

#         return context

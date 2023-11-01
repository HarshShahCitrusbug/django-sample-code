from django.urls import path

from embermail.interface.profiles import views

app_name = "profiles"
urlpatterns = [
    # User Personal Data Update
    path('user-profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('member/list/', views.MemberListView.as_view(), name='member_list'),
    path('member/list/search/', views.MemberListAJAXView.as_view(), name='member_list_search'),
    path('billing/section/', views.BillingSectionView.as_view(), name='billing_section'),
    path('billing/section/search/', views.BillingSearchAJAXView.as_view(), name='billing_search'),
]

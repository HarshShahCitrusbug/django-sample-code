from django.urls import path

from embermail.interface.templates import views

app_name = "templates"
urlpatterns = [
    # Template CURD
    path('list/', views.TemplateListView.as_view(), name='template_list'),
    path('add/', views.AddNewTemplateAJAXView.as_view(), name='template_add'),
    path('update/', views.UpdateTemplateAJAXView.as_view(), name='template_update'),
    path('update/status/', views.UpdateTemplateStatusAJAXView.as_view(), name='template_status'),
    path('delete/', views.DeleteTemplateAJAXView.as_view(), name='template_delete'),
    path('add/default/', views.AddDefaultTemplateAJAXView.as_view(), name='add_default_template'),

    # Thread
    path('threads/list/<uuid:template_id>/', views.ThreadListView.as_view(), name='thread_list'),
    path('threads/add/', views.AddNewThreadAJAXView.as_view(), name='thread_add'),
    path('threads/update/', views.UpdateThreadAJAXView.as_view(), name='thread_update'),
    path('threads/delete/', views.DeleteThreadAJAXView.as_view(), name='thread_delete'),
]

from django.contrib import admin

from embermail.domain.templates.models import Thread, Template


class TemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'subject', 'warmup_email', 'user_id', 'is_selected', 'is_general', 'is_active')
    search_fields = ('id', 'name', 'subject', 'warmup_email', 'user_id')
    list_filter = ('is_active', 'subject', 'warmup_email',)
    order_by = ('-updated_at',)


class ThreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'template_id', 'body', 'thread_ordering_number')
    search_fields = ('id', 'template_id')
    list_filter = ('is_active',)
    order_by = ('thread_ordering_number',)


admin.site.register(Thread, ThreadAdmin)
admin.site.register(Template, TemplateAdmin)

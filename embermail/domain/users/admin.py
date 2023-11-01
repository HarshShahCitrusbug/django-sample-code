from django.contrib import admin

from embermail.domain.users.models import User, ForgotPassword, VisitedUser, Inquiry


class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'id', 'is_verified', 'is_master_user', 'users_master_id', 'stripe_customer_id')
    search_fields = ('email', 'first_name', 'last_name', 'stripe_customer_id')
    list_filter = ('is_master_user', 'is_verified', 'is_active', 'is_deleted')


class ForgotPasswordAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'password_token', 'password_token_expiry')
    search_fields = ('user_id',)


class VisitedUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'ip_address')
    search_fields = ('email', 'ip_address')
    list_filter = ('ip_address',)


class InquiryAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'contact_message', 'created_at', 'is_solved')
    search_fields = ('email', 'contact_message')
    list_filter = ('is_solved',)
    ordering = ('-created_at', 'is_solved', 'email')


admin.site.register(User, UserAdmin)
admin.site.register(ForgotPassword, ForgotPasswordAdmin)
admin.site.register(VisitedUser, VisitedUserAdmin)
admin.site.register(Inquiry, InquiryAdmin)

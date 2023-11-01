from django.contrib import admin

from embermail.domain.payments.models import Plan, PaymentMethod, Payment


class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_amount', 'plan_duration', 'stripe_price_id', 'stripe_product_id')
    search_fields = ('id', 'name', 'stripe_price_id', 'stripe_product_id')
    list_filter = ('is_active',)


class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'stripe_payment_method', 'updated_at')
    search_fields = ('user_id', 'stripe_payment_method__id')
    list_filter = ('is_active',)
    order_by = ('-updated_at',)


class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'warmup_email', 'master_user_id', 'purchased_plan_id', 'payment_status', 'updated_at',
        'stripe_subscription')
    search_fields = ('id', 'warmup_email', 'master_user_id',)
    list_filter = ('payment_status', 'purchased_plan_id')
    order_by = ('-updated_at',)


admin.site.register(Plan, PlanAdmin)
admin.site.register(PaymentMethod, PaymentMethodAdmin)
admin.site.register(Payment, PaymentAdmin)

from django.contrib import admin
from .models import ApprovalLog, ClaimAttachment, ExpenseClaim, PolicyRule, Reimbursement


class AttachmentInline(admin.TabularInline):
    model  = ClaimAttachment
    extra  = 0
    fields = ['file_type', 'filename', 'file_size', 'uploaded_by', 'uploaded_at']
    readonly_fields = ['uploaded_at']


class ApprovalLogInline(admin.TabularInline):
    model  = ApprovalLog
    extra  = 0
    fields = ['action', 'acted_by', 'notes', 'created_at']
    readonly_fields = ['created_at']


@admin.register(ExpenseClaim)
class ExpenseClaimAdmin(admin.ModelAdmin):
    list_display  = ['claim_number', 'title', 'expense_category', 'amount',
                     'status', 'submitted_by', 'created_at']
    list_filter   = ['status', 'claim_type', 'expense_category']
    search_fields = ['claim_number', 'title', 'submitted_by__username']
    readonly_fields = ['claim_number', 'submitted_at', 'created_at', 'updated_at']
    inlines       = [AttachmentInline, ApprovalLogInline]


@admin.register(PolicyRule)
class PolicyRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule_type', 'expense_category', 'threshold_amount', 'is_active']
    list_filter  = ['rule_type', 'is_active']


@admin.register(Reimbursement)
class ReimbursementAdmin(admin.ModelAdmin):
    list_display = ['claim', 'amount_paid', 'payment_method', 'paid_by', 'paid_at']
    readonly_fields = ['paid_at']

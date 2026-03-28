from django.contrib import admin
from .models import Budget, BudgetCategory, BudgetCycle, BudgetLineItem, BudgetRevision


@admin.register(BudgetCycle)
class BudgetCycleAdmin(admin.ModelAdmin):
    list_display  = ['name', 'cycle_type', 'start_date', 'end_date', 'status']
    list_filter   = ['status', 'cycle_type']
    search_fields = ['name']


@admin.register(BudgetCategory)
class BudgetCategoryAdmin(admin.ModelAdmin):
    list_display  = ['code', 'name', 'is_active']
    list_filter   = ['is_active']
    search_fields = ['name', 'code']


class BudgetLineItemInline(admin.TabularInline):
    model  = BudgetLineItem
    extra  = 0
    fields = ['category', 'planned_amount', 'actual_amount']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display  = ['name', 'level', 'department', 'cycle', 'planned_amount', 'actual_amount', 'status']
    list_filter   = ['level', 'status', 'cycle']
    search_fields = ['name', 'department', 'project_code']
    inlines       = [BudgetLineItemInline]
    readonly_fields = ['actual_amount', 'reserved_amount', 'created_by', 'created_at']


@admin.register(BudgetRevision)
class BudgetRevisionAdmin(admin.ModelAdmin):
    list_display  = ['budget', 'old_amount', 'new_amount', 'revised_by', 'created_at']
    readonly_fields = ['budget', 'revised_by', 'old_amount', 'new_amount', 'reason', 'created_at']

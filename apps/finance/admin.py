from django.contrib import admin
from .models import ExpenseCategory, Expense, IncomeCategory, Income, FinancialSummary


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_type', 'is_active', 'order']
    list_filter = ['category_type', 'is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'total_amount', 'status', 'expense_date', 'created_by']
    list_filter = ['status', 'category', 'payment_method', 'expense_date']
    search_fields = ['title', 'vendor_name', 'description']
    date_hierarchy = 'expense_date'


@admin.register(IncomeCategory)
class IncomeCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'is_auto_imported', 'is_active', 'order']
    list_filter = ['source_type', 'is_auto_imported', 'is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'total_amount', 'status', 'income_date', 'is_auto_imported']
    list_filter = ['status', 'category', 'is_auto_imported', 'income_date']
    search_fields = ['title', 'payer_name', 'description']
    date_hierarchy = 'income_date'


@admin.register(FinancialSummary)
class FinancialSummaryAdmin(admin.ModelAdmin):
    list_display = ['summary_type', 'period_start', 'period_end', 'total_income', 'total_expense', 'net_profit']
    list_filter = ['summary_type']
    date_hierarchy = 'period_start'

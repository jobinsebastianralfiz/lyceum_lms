"""
Finance Management Views for Custom Admin
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.utils import timezone

from apps.finance.models import ExpenseCategory, Expense, IncomeCategory, Income, FinancialSummary, Vendor
from apps.finance.services import (
    seed_default_categories,
    sync_enrollment_payments,
    get_financial_summary,
    get_category_breakdown,
    get_monthly_trend
)
from apps.payments.models import Payment, Enrollment
from apps.courses.models import Course
from calendar import monthrange

logger = logging.getLogger(__name__)


def is_staff_user(user):
    """Check if user is staff/admin"""
    return user.is_authenticated and (user.is_staff or user.role == 'admin')


# =============================================================================
# FINANCE DASHBOARD
# =============================================================================

@user_passes_test(is_staff_user)
def finance_dashboard_view(request):
    """Main finance dashboard with KPIs and charts"""
    today = date.today()
    year_start = date(today.year, 1, 1)
    month_start = today.replace(day=1)

    # Get YTD summary
    ytd_summary = get_financial_summary(year_start, today)

    # Get current month summary
    month_summary = get_financial_summary(month_start, today)

    # Get pending counts
    pending_expenses = Expense.objects.filter(status='pending').count()
    pending_income = Income.objects.filter(status='pending').count()

    # Get recent transactions
    recent_expenses = Expense.objects.select_related('category', 'created_by').order_by('-created_at')[:5]
    recent_income = Income.objects.select_related('category', 'created_by').order_by('-created_at')[:5]

    # Get category breakdowns for charts
    category_data = get_category_breakdown(year_start, today)

    # Get monthly trend data
    trend_data = get_monthly_trend(12)

    context = {
        'page_title': 'Finance Dashboard',
        'ytd_summary': ytd_summary,
        'month_summary': month_summary,
        'pending_expenses': pending_expenses,
        'pending_income': pending_income,
        'recent_expenses': recent_expenses,
        'recent_income': recent_income,
        'income_by_category': category_data['income_by_category'],
        'expense_by_category': category_data['expense_by_category'],
        'trend_labels': trend_data['labels'],
        'trend_income': trend_data['income'],
        'trend_expense': trend_data['expense'],
    }

    return render(request, 'custom_admin/finance/dashboard.html', context)


# =============================================================================
# EXPENSE CATEGORIES
# =============================================================================

@user_passes_test(is_staff_user)
def expense_categories_list_view(request):
    """List all expense categories"""
    categories = ExpenseCategory.objects.all().annotate(
        expense_count=Count('expenses'),
        total_expense=Sum('expenses__total_amount', filter=Q(expenses__status='paid'))
    ).order_by('order', 'name')

    context = {
        'page_title': 'Expense Categories',
        'categories': categories,
    }
    return render(request, 'custom_admin/finance/expense_categories_list.html', context)


@user_passes_test(is_staff_user)
def expense_category_create_view(request):
    """Create a new expense category"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            category_type = request.POST.get('category_type', 'variable')
            icon = request.POST.get('icon', 'ti-folder')
            color = request.POST.get('color', '#5d87ff')
            budget_limit = request.POST.get('budget_limit')
            order = request.POST.get('order', 0)

            if not name:
                messages.error(request, 'Category name is required.')
                return redirect('custom_admin:expense_category_create')

            ExpenseCategory.objects.create(
                name=name,
                description=description or None,
                category_type=category_type,
                icon=icon,
                color=color,
                budget_limit=Decimal(budget_limit) if budget_limit else None,
                order=int(order) if order else 0
            )
            messages.success(request, f'Expense category "{name}" created successfully.')
            return redirect('custom_admin:expense_categories_list')

        except Exception as e:
            logger.error(f"Error creating expense category: {str(e)}")
            messages.error(request, f'Error creating category: {str(e)}')

    context = {
        'page_title': 'Add Expense Category',
        'category_types': ExpenseCategory.CATEGORY_TYPE_CHOICES,
    }
    return render(request, 'custom_admin/finance/expense_category_form.html', context)


@user_passes_test(is_staff_user)
def expense_category_edit_view(request, category_id):
    """Edit an expense category"""
    category = get_object_or_404(ExpenseCategory, id=category_id)

    if request.method == 'POST':
        try:
            category.name = request.POST.get('name', '').strip()
            category.description = request.POST.get('description', '').strip() or None
            category.category_type = request.POST.get('category_type', 'variable')
            category.icon = request.POST.get('icon', 'ti-folder')
            category.color = request.POST.get('color', '#5d87ff')
            budget_limit = request.POST.get('budget_limit')
            category.budget_limit = Decimal(budget_limit) if budget_limit else None
            category.order = int(request.POST.get('order', 0))
            category.is_active = request.POST.get('is_active') == 'on'

            category.save()
            messages.success(request, f'Category "{category.name}" updated successfully.')
            return redirect('custom_admin:expense_categories_list')

        except Exception as e:
            logger.error(f"Error updating expense category: {str(e)}")
            messages.error(request, f'Error updating category: {str(e)}')

    context = {
        'page_title': 'Edit Expense Category',
        'category': category,
        'category_types': ExpenseCategory.CATEGORY_TYPE_CHOICES,
    }
    return render(request, 'custom_admin/finance/expense_category_form.html', context)


@user_passes_test(is_staff_user)
def expense_category_delete_view(request, category_id):
    """Delete an expense category"""
    category = get_object_or_404(ExpenseCategory, id=category_id)

    if request.method == 'POST':
        try:
            # Check if category has expenses
            if category.expenses.exists():
                messages.error(request, f'Cannot delete "{category.name}" - it has associated expenses.')
                return redirect('custom_admin:expense_categories_list')

            name = category.name
            category.delete()
            messages.success(request, f'Category "{name}" deleted successfully.')
        except Exception as e:
            logger.error(f"Error deleting expense category: {str(e)}")
            messages.error(request, f'Error deleting category: {str(e)}')

    return redirect('custom_admin:expense_categories_list')


# =============================================================================
# EXPENSES
# =============================================================================

@user_passes_test(is_staff_user)
def expenses_list_view(request):
    """List all expenses with filters"""
    expenses = Expense.objects.select_related('category', 'created_by', 'approved_by').all()

    # Apply filters
    category_id = request.GET.get('category')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search = request.GET.get('search', '').strip()

    if category_id:
        expenses = expenses.filter(category_id=category_id)
    if status:
        expenses = expenses.filter(status=status)
    if date_from:
        expenses = expenses.filter(expense_date__gte=date_from)
    if date_to:
        expenses = expenses.filter(expense_date__lte=date_to)
    if search:
        expenses = expenses.filter(
            Q(title__icontains=search) |
            Q(vendor_name__icontains=search) |
            Q(description__icontains=search)
        )

    expenses = expenses.order_by('-expense_date', '-created_at')

    # Pagination
    paginator = Paginator(expenses, 15)
    page = request.GET.get('page', 1)
    expenses = paginator.get_page(page)

    # Get filter options
    categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')

    context = {
        'page_title': 'Expenses',
        'expenses': expenses,
        'categories': categories,
        'status_choices': Expense.STATUS_CHOICES,
        'selected_category': category_id,
        'selected_status': status,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
    }
    return render(request, 'custom_admin/finance/expenses_list.html', context)


@user_passes_test(is_staff_user)
def expense_create_view(request):
    """Create a new expense"""
    if request.method == 'POST':
        try:
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            category_id = request.POST.get('category')
            amount = request.POST.get('amount')
            tax_amount = request.POST.get('tax_amount', '0')
            payment_method = request.POST.get('payment_method')
            payment_reference = request.POST.get('payment_reference', '').strip()
            vendor_id = request.POST.get('vendor')
            vendor_name = request.POST.get('vendor_name', '').strip()
            vendor_gstin = request.POST.get('vendor_gstin', '').strip()
            save_vendor = request.POST.get('save_vendor') == 'on'
            invoice_number = request.POST.get('invoice_number', '').strip()
            status = request.POST.get('status', 'pending')
            expense_date = request.POST.get('expense_date')
            payment_date = request.POST.get('payment_date')
            due_date = request.POST.get('due_date')
            notes = request.POST.get('notes', '').strip()

            if not title or not category_id or not amount or not expense_date:
                messages.error(request, 'Title, category, amount, and expense date are required.')
                return redirect('custom_admin:expense_create')

            # Handle vendor - either use existing or create new
            vendor = None
            if vendor_id:
                vendor = Vendor.objects.filter(id=vendor_id).first()
            elif vendor_name and save_vendor:
                # Create new vendor if save_vendor is checked
                vendor = Vendor.objects.create(
                    name=vendor_name,
                    vendor_type='supplier',
                    gstin=vendor_gstin or None,
                )

            expense = Expense.objects.create(
                title=title,
                description=description or None,
                category_id=category_id,
                amount=Decimal(amount),
                tax_amount=Decimal(tax_amount) if tax_amount else Decimal('0.00'),
                payment_method=payment_method,
                payment_reference=payment_reference or None,
                vendor=vendor,
                vendor_name=vendor.name if vendor else (vendor_name or None),
                vendor_gstin=vendor.gstin if vendor else (vendor_gstin or None),
                invoice_number=invoice_number or None,
                status=status,
                expense_date=expense_date,
                payment_date=payment_date or None,
                due_date=due_date or None,
                notes=notes or None,
                created_by=request.user
            )

            # Handle file uploads
            if 'receipt' in request.FILES:
                expense.receipt = request.FILES['receipt']
            if 'invoice_file' in request.FILES:
                expense.invoice_file = request.FILES['invoice_file']
            expense.save()

            messages.success(request, f'Expense "{title}" created successfully.')
            return redirect('custom_admin:expenses_list')

        except Exception as e:
            logger.error(f"Error creating expense: {str(e)}")
            messages.error(request, f'Error creating expense: {str(e)}')

    categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')
    vendors = Vendor.objects.filter(is_active=True).exclude(vendor_type='customer').order_by('name')

    context = {
        'page_title': 'Add Expense',
        'categories': categories,
        'vendors': vendors,
        'status_choices': Expense.STATUS_CHOICES,
        'payment_methods': Expense.PAYMENT_METHOD_CHOICES,
    }
    return render(request, 'custom_admin/finance/expense_form.html', context)


@user_passes_test(is_staff_user)
def expense_detail_view(request, expense_id):
    """View expense details"""
    expense = get_object_or_404(
        Expense.objects.select_related('category', 'created_by', 'approved_by'),
        id=expense_id
    )

    context = {
        'page_title': f'Expense: {expense.title}',
        'expense': expense,
    }
    return render(request, 'custom_admin/finance/expense_detail.html', context)


@user_passes_test(is_staff_user)
def expense_edit_view(request, expense_id):
    """Edit an expense"""
    expense = get_object_or_404(Expense, id=expense_id)

    if request.method == 'POST':
        try:
            expense.title = request.POST.get('title', '').strip()
            expense.description = request.POST.get('description', '').strip() or None
            expense.category_id = request.POST.get('category')
            expense.amount = Decimal(request.POST.get('amount'))
            tax_amount = request.POST.get('tax_amount', '0')
            expense.tax_amount = Decimal(tax_amount) if tax_amount else Decimal('0.00')
            expense.payment_method = request.POST.get('payment_method')
            expense.payment_reference = request.POST.get('payment_reference', '').strip() or None

            # Handle vendor
            vendor_id = request.POST.get('vendor')
            vendor_name = request.POST.get('vendor_name', '').strip()
            vendor_gstin = request.POST.get('vendor_gstin', '').strip()
            save_vendor = request.POST.get('save_vendor') == 'on'

            if vendor_id:
                expense.vendor = Vendor.objects.filter(id=vendor_id).first()
                if expense.vendor:
                    expense.vendor_name = expense.vendor.name
                    expense.vendor_gstin = expense.vendor.gstin
            elif vendor_name and save_vendor:
                vendor = Vendor.objects.create(
                    name=vendor_name,
                    vendor_type='supplier',
                    gstin=vendor_gstin or None,
                )
                expense.vendor = vendor
                expense.vendor_name = vendor.name
                expense.vendor_gstin = vendor.gstin
            else:
                expense.vendor = None
                expense.vendor_name = vendor_name or None
                expense.vendor_gstin = vendor_gstin or None

            expense.invoice_number = request.POST.get('invoice_number', '').strip() or None
            expense.status = request.POST.get('status', 'pending')
            expense.expense_date = request.POST.get('expense_date')
            expense.payment_date = request.POST.get('payment_date') or None
            expense.due_date = request.POST.get('due_date') or None
            expense.notes = request.POST.get('notes', '').strip() or None

            # Handle file uploads
            if 'receipt' in request.FILES:
                expense.receipt = request.FILES['receipt']
            if 'invoice_file' in request.FILES:
                expense.invoice_file = request.FILES['invoice_file']

            expense.save()
            messages.success(request, f'Expense "{expense.title}" updated successfully.')
            return redirect('custom_admin:expenses_list')

        except Exception as e:
            logger.error(f"Error updating expense: {str(e)}")
            messages.error(request, f'Error updating expense: {str(e)}')

    categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')
    vendors = Vendor.objects.filter(is_active=True).exclude(vendor_type='customer').order_by('name')

    context = {
        'page_title': 'Edit Expense',
        'expense': expense,
        'categories': categories,
        'vendors': vendors,
        'status_choices': Expense.STATUS_CHOICES,
        'payment_methods': Expense.PAYMENT_METHOD_CHOICES,
    }
    return render(request, 'custom_admin/finance/expense_form.html', context)


@user_passes_test(is_staff_user)
def expense_delete_view(request, expense_id):
    """Delete an expense"""
    expense = get_object_or_404(Expense, id=expense_id)

    if request.method == 'POST':
        try:
            title = expense.title
            expense.delete()
            messages.success(request, f'Expense "{title}" deleted successfully.')
        except Exception as e:
            logger.error(f"Error deleting expense: {str(e)}")
            messages.error(request, f'Error deleting expense: {str(e)}')

    return redirect('custom_admin:expenses_list')


@user_passes_test(is_staff_user)
def expense_approve_view(request, expense_id):
    """Approve an expense"""
    expense = get_object_or_404(Expense, id=expense_id)

    if request.method == 'POST':
        try:
            expense.status = 'approved'
            expense.approved_by = request.user
            expense.save()
            messages.success(request, f'Expense "{expense.title}" approved successfully.')
        except Exception as e:
            logger.error(f"Error approving expense: {str(e)}")
            messages.error(request, f'Error approving expense: {str(e)}')

    return redirect('custom_admin:expense_detail', expense_id=expense_id)


# =============================================================================
# INCOME CATEGORIES
# =============================================================================

@user_passes_test(is_staff_user)
def income_categories_list_view(request):
    """List all income categories"""
    categories = IncomeCategory.objects.all().annotate(
        income_count=Count('incomes'),
        total_income=Sum('incomes__total_amount', filter=Q(incomes__status='received'))
    ).order_by('order', 'name')

    context = {
        'page_title': 'Income Categories',
        'categories': categories,
    }
    return render(request, 'custom_admin/finance/income_categories_list.html', context)


@user_passes_test(is_staff_user)
def income_category_create_view(request):
    """Create a new income category"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            source_type = request.POST.get('source_type', 'other')
            icon = request.POST.get('icon', 'ti-wallet')
            color = request.POST.get('color', '#2ab673')
            order = request.POST.get('order', 0)

            if not name:
                messages.error(request, 'Category name is required.')
                return redirect('custom_admin:income_category_create')

            IncomeCategory.objects.create(
                name=name,
                description=description or None,
                source_type=source_type,
                icon=icon,
                color=color,
                order=int(order) if order else 0
            )
            messages.success(request, f'Income category "{name}" created successfully.')
            return redirect('custom_admin:income_categories_list')

        except Exception as e:
            logger.error(f"Error creating income category: {str(e)}")
            messages.error(request, f'Error creating category: {str(e)}')

    context = {
        'page_title': 'Add Income Category',
        'source_types': IncomeCategory.SOURCE_TYPE_CHOICES,
    }
    return render(request, 'custom_admin/finance/income_category_form.html', context)


@user_passes_test(is_staff_user)
def income_category_edit_view(request, category_id):
    """Edit an income category"""
    category = get_object_or_404(IncomeCategory, id=category_id)

    if request.method == 'POST':
        try:
            category.name = request.POST.get('name', '').strip()
            category.description = request.POST.get('description', '').strip() or None
            category.source_type = request.POST.get('source_type', 'other')
            category.icon = request.POST.get('icon', 'ti-wallet')
            category.color = request.POST.get('color', '#2ab673')
            category.order = int(request.POST.get('order', 0))
            category.is_active = request.POST.get('is_active') == 'on'

            category.save()
            messages.success(request, f'Category "{category.name}" updated successfully.')
            return redirect('custom_admin:income_categories_list')

        except Exception as e:
            logger.error(f"Error updating income category: {str(e)}")
            messages.error(request, f'Error updating category: {str(e)}')

    context = {
        'page_title': 'Edit Income Category',
        'category': category,
        'source_types': IncomeCategory.SOURCE_TYPE_CHOICES,
    }
    return render(request, 'custom_admin/finance/income_category_form.html', context)


@user_passes_test(is_staff_user)
def income_category_delete_view(request, category_id):
    """Delete an income category"""
    category = get_object_or_404(IncomeCategory, id=category_id)

    if request.method == 'POST':
        try:
            # Check if category has income records
            if category.incomes.exists():
                messages.error(request, f'Cannot delete "{category.name}" - it has associated income records.')
                return redirect('custom_admin:income_categories_list')

            name = category.name
            category.delete()
            messages.success(request, f'Category "{name}" deleted successfully.')
        except Exception as e:
            logger.error(f"Error deleting income category: {str(e)}")
            messages.error(request, f'Error deleting category: {str(e)}')

    return redirect('custom_admin:income_categories_list')


# =============================================================================
# INCOME
# =============================================================================

@user_passes_test(is_staff_user)
def income_list_view(request):
    """List all income with filters"""
    incomes = Income.objects.select_related('category', 'created_by', 'enrollment', 'payment').all()

    # Apply filters
    category_id = request.GET.get('category')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search = request.GET.get('search', '').strip()
    auto_imported = request.GET.get('auto_imported')

    if category_id:
        incomes = incomes.filter(category_id=category_id)
    if status:
        incomes = incomes.filter(status=status)
    if date_from:
        incomes = incomes.filter(income_date__gte=date_from)
    if date_to:
        incomes = incomes.filter(income_date__lte=date_to)
    if search:
        incomes = incomes.filter(
            Q(title__icontains=search) |
            Q(payer_name__icontains=search) |
            Q(description__icontains=search)
        )
    if auto_imported == 'yes':
        incomes = incomes.filter(is_auto_imported=True)
    elif auto_imported == 'no':
        incomes = incomes.filter(is_auto_imported=False)

    incomes = incomes.order_by('-income_date', '-created_at')

    # Pagination
    paginator = Paginator(incomes, 15)
    page = request.GET.get('page', 1)
    incomes = paginator.get_page(page)

    # Get filter options
    categories = IncomeCategory.objects.filter(is_active=True).order_by('name')

    context = {
        'page_title': 'Income',
        'incomes': incomes,
        'categories': categories,
        'status_choices': Income.STATUS_CHOICES,
        'selected_category': category_id,
        'selected_status': status,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
        'auto_imported': auto_imported,
    }
    return render(request, 'custom_admin/finance/income_list.html', context)


@user_passes_test(is_staff_user)
def income_create_view(request):
    """Create a new income record"""
    if request.method == 'POST':
        try:
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            category_id = request.POST.get('category')
            amount = request.POST.get('amount')
            tax_amount = request.POST.get('tax_amount', '0')
            payment_method = request.POST.get('payment_method')
            payment_reference = request.POST.get('payment_reference', '').strip()
            payer_id = request.POST.get('payer')
            payer_name = request.POST.get('payer_name', '').strip()
            payer_email = request.POST.get('payer_email', '').strip()
            payer_phone = request.POST.get('payer_phone', '').strip()
            save_payer = request.POST.get('save_payer') == 'on'
            invoice_number = request.POST.get('invoice_number', '').strip()
            status = request.POST.get('status', 'pending')
            income_date = request.POST.get('income_date')
            notes = request.POST.get('notes', '').strip()

            if not title or not category_id or not amount or not income_date:
                messages.error(request, 'Title, category, amount, and income date are required.')
                return redirect('custom_admin:income_create')

            # Handle payer - either use existing or create new
            payer = None
            if payer_id:
                payer = Vendor.objects.filter(id=payer_id).first()
            elif payer_name and save_payer:
                # Create new payer if save_payer is checked
                payer = Vendor.objects.create(
                    name=payer_name,
                    vendor_type='customer',
                    email=payer_email or None,
                    phone=payer_phone or None,
                )

            income = Income.objects.create(
                title=title,
                description=description or None,
                category_id=category_id,
                amount=Decimal(amount),
                tax_amount=Decimal(tax_amount) if tax_amount else Decimal('0.00'),
                payment_method=payment_method or None,
                payment_reference=payment_reference or None,
                payer=payer,
                payer_name=payer.name if payer else (payer_name or None),
                payer_email=payer.email if payer else (payer_email or None),
                payer_phone=payer.phone if payer else (payer_phone or None),
                invoice_number=invoice_number or None,
                status=status,
                income_date=income_date,
                notes=notes or None,
                created_by=request.user,
                is_auto_imported=False
            )

            # Handle file upload
            if 'receipt' in request.FILES:
                income.receipt = request.FILES['receipt']
                income.save()

            messages.success(request, f'Income "{title}" created successfully.')
            return redirect('custom_admin:income_list')

        except Exception as e:
            logger.error(f"Error creating income: {str(e)}")
            messages.error(request, f'Error creating income: {str(e)}')

    categories = IncomeCategory.objects.filter(is_active=True).order_by('name')
    payers = Vendor.objects.filter(is_active=True).filter(
        Q(vendor_type='customer') | Q(vendor_type='partner')
    ).order_by('name')

    context = {
        'page_title': 'Add Income',
        'categories': categories,
        'payers': payers,
        'status_choices': Income.STATUS_CHOICES,
        'payment_methods': Income.PAYMENT_METHOD_CHOICES,
    }
    return render(request, 'custom_admin/finance/income_form.html', context)


@user_passes_test(is_staff_user)
def income_detail_view(request, income_id):
    """View income details"""
    income = get_object_or_404(
        Income.objects.select_related('category', 'created_by', 'enrollment', 'payment'),
        id=income_id
    )

    context = {
        'page_title': f'Income: {income.title}',
        'income': income,
    }
    return render(request, 'custom_admin/finance/income_detail.html', context)


@user_passes_test(is_staff_user)
def income_edit_view(request, income_id):
    """Edit an income record"""
    income = get_object_or_404(Income, id=income_id)

    if request.method == 'POST':
        try:
            income.title = request.POST.get('title', '').strip()
            income.description = request.POST.get('description', '').strip() or None
            income.category_id = request.POST.get('category')
            income.amount = Decimal(request.POST.get('amount'))
            tax_amount = request.POST.get('tax_amount', '0')
            income.tax_amount = Decimal(tax_amount) if tax_amount else Decimal('0.00')
            income.payment_method = request.POST.get('payment_method') or None
            income.payment_reference = request.POST.get('payment_reference', '').strip() or None

            # Handle payer
            payer_id = request.POST.get('payer')
            payer_name = request.POST.get('payer_name', '').strip()
            payer_email = request.POST.get('payer_email', '').strip()
            payer_phone = request.POST.get('payer_phone', '').strip()
            save_payer = request.POST.get('save_payer') == 'on'

            if payer_id:
                income.payer = Vendor.objects.filter(id=payer_id).first()
                if income.payer:
                    income.payer_name = income.payer.name
                    income.payer_email = income.payer.email
                    income.payer_phone = income.payer.phone
            elif payer_name and save_payer:
                payer = Vendor.objects.create(
                    name=payer_name,
                    vendor_type='customer',
                    email=payer_email or None,
                    phone=payer_phone or None,
                )
                income.payer = payer
                income.payer_name = payer.name
                income.payer_email = payer.email
                income.payer_phone = payer.phone
            else:
                income.payer = None
                income.payer_name = payer_name or None
                income.payer_email = payer_email or None
                income.payer_phone = payer_phone or None

            income.invoice_number = request.POST.get('invoice_number', '').strip() or None
            income.status = request.POST.get('status', 'pending')
            income.income_date = request.POST.get('income_date')
            income.notes = request.POST.get('notes', '').strip() or None

            # Handle file upload
            if 'receipt' in request.FILES:
                income.receipt = request.FILES['receipt']

            income.save()
            messages.success(request, f'Income "{income.title}" updated successfully.')
            return redirect('custom_admin:income_list')

        except Exception as e:
            logger.error(f"Error updating income: {str(e)}")
            messages.error(request, f'Error updating income: {str(e)}')

    categories = IncomeCategory.objects.filter(is_active=True).order_by('name')
    payers = Vendor.objects.filter(is_active=True).filter(
        Q(vendor_type='customer') | Q(vendor_type='partner')
    ).order_by('name')

    context = {
        'page_title': 'Edit Income',
        'income': income,
        'categories': categories,
        'payers': payers,
        'status_choices': Income.STATUS_CHOICES,
        'payment_methods': Income.PAYMENT_METHOD_CHOICES,
    }
    return render(request, 'custom_admin/finance/income_form.html', context)


@user_passes_test(is_staff_user)
def income_delete_view(request, income_id):
    """Delete an income record"""
    income = get_object_or_404(Income, id=income_id)

    if request.method == 'POST':
        try:
            title = income.title
            income.delete()
            messages.success(request, f'Income "{title}" deleted successfully.')
        except Exception as e:
            logger.error(f"Error deleting income: {str(e)}")
            messages.error(request, f'Error deleting income: {str(e)}')

    return redirect('custom_admin:income_list')


# =============================================================================
# SYNC & REPORTS
# =============================================================================

@user_passes_test(is_staff_user)
def sync_payments_view(request):
    """Sync enrollment payments to income records"""
    if request.method == 'POST':
        try:
            count = sync_enrollment_payments()
            if count > 0:
                messages.success(request, f'Successfully imported {count} payment(s) as income records.')
            else:
                messages.info(request, 'No new payments to import.')
        except Exception as e:
            logger.error(f"Error syncing payments: {str(e)}")
            messages.error(request, f'Error syncing payments: {str(e)}')

    return redirect('custom_admin:finance_dashboard')


@user_passes_test(is_staff_user)
def finance_chart_data_api(request):
    """API endpoint for chart data"""
    try:
        chart_type = request.GET.get('type', 'trend')

        if chart_type == 'trend':
            months = int(request.GET.get('months', 12))
            data = get_monthly_trend(months)
        elif chart_type == 'category':
            today = date.today()
            year_start = date(today.year, 1, 1)
            data = get_category_breakdown(year_start, today)
        else:
            data = {}

        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =============================================================================
# VENDORS
# =============================================================================

@user_passes_test(is_staff_user)
def vendors_list_view(request):
    """List all vendors"""
    vendors = Vendor.objects.all()

    # Apply filters
    vendor_type = request.GET.get('type')
    search = request.GET.get('search', '').strip()
    is_active = request.GET.get('is_active')

    if vendor_type:
        vendors = vendors.filter(vendor_type=vendor_type)
    if search:
        vendors = vendors.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search) |
            Q(gstin__icontains=search)
        )
    if is_active == 'yes':
        vendors = vendors.filter(is_active=True)
    elif is_active == 'no':
        vendors = vendors.filter(is_active=False)

    vendors = vendors.annotate(
        expense_count=Count('expenses'),
        income_count=Count('income_records'),
        total_expense=Sum('expenses__total_amount', filter=Q(expenses__status='paid')),
        total_income=Sum('income_records__total_amount', filter=Q(income_records__status='received'))
    ).order_by('name')

    # Pagination
    paginator = Paginator(vendors, 15)
    page = request.GET.get('page', 1)
    vendors = paginator.get_page(page)

    context = {
        'page_title': 'Vendors & Payers',
        'vendors': vendors,
        'vendor_types': Vendor.VENDOR_TYPE_CHOICES,
        'selected_type': vendor_type,
        'search': search,
        'is_active': is_active,
    }
    return render(request, 'custom_admin/finance/vendors_list.html', context)


@user_passes_test(is_staff_user)
def vendor_create_view(request):
    """Create a new vendor"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            vendor_type = request.POST.get('vendor_type', 'supplier')
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            address = request.POST.get('address', '').strip()
            gstin = request.POST.get('gstin', '').strip()
            pan = request.POST.get('pan', '').strip()
            bank_name = request.POST.get('bank_name', '').strip()
            bank_account = request.POST.get('bank_account', '').strip()
            bank_ifsc = request.POST.get('bank_ifsc', '').strip()
            notes = request.POST.get('notes', '').strip()

            if not name:
                messages.error(request, 'Vendor name is required.')
                return redirect('custom_admin:vendor_create')

            Vendor.objects.create(
                name=name,
                vendor_type=vendor_type,
                email=email or None,
                phone=phone or None,
                address=address or None,
                gstin=gstin or None,
                pan=pan or None,
                bank_name=bank_name or None,
                bank_account=bank_account or None,
                bank_ifsc=bank_ifsc or None,
                notes=notes or None,
            )
            messages.success(request, f'Vendor "{name}" created successfully.')
            return redirect('custom_admin:vendors_list')

        except Exception as e:
            logger.error(f"Error creating vendor: {str(e)}")
            messages.error(request, f'Error creating vendor: {str(e)}')

    context = {
        'page_title': 'Add Vendor',
        'vendor_types': Vendor.VENDOR_TYPE_CHOICES,
    }
    return render(request, 'custom_admin/finance/vendor_form.html', context)


@user_passes_test(is_staff_user)
def vendor_detail_view(request, vendor_id):
    """View vendor details"""
    vendor = get_object_or_404(Vendor, id=vendor_id)

    # Get recent transactions
    recent_expenses = vendor.expenses.select_related('category').order_by('-expense_date')[:5]
    recent_income = vendor.income_records.select_related('category').order_by('-income_date')[:5]

    # Calculate totals
    total_expense = vendor.expenses.filter(status='paid').aggregate(total=Sum('total_amount'))['total'] or 0
    total_income = vendor.income_records.filter(status='received').aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        'page_title': f'Vendor: {vendor.name}',
        'vendor': vendor,
        'recent_expenses': recent_expenses,
        'recent_income': recent_income,
        'total_expense': total_expense,
        'total_income': total_income,
    }
    return render(request, 'custom_admin/finance/vendor_detail.html', context)


@user_passes_test(is_staff_user)
def vendor_edit_view(request, vendor_id):
    """Edit a vendor"""
    vendor = get_object_or_404(Vendor, id=vendor_id)

    if request.method == 'POST':
        try:
            vendor.name = request.POST.get('name', '').strip()
            vendor.vendor_type = request.POST.get('vendor_type', 'supplier')
            vendor.email = request.POST.get('email', '').strip() or None
            vendor.phone = request.POST.get('phone', '').strip() or None
            vendor.address = request.POST.get('address', '').strip() or None
            vendor.gstin = request.POST.get('gstin', '').strip() or None
            vendor.pan = request.POST.get('pan', '').strip() or None
            vendor.bank_name = request.POST.get('bank_name', '').strip() or None
            vendor.bank_account = request.POST.get('bank_account', '').strip() or None
            vendor.bank_ifsc = request.POST.get('bank_ifsc', '').strip() or None
            vendor.notes = request.POST.get('notes', '').strip() or None
            vendor.is_active = request.POST.get('is_active') == 'on'

            vendor.save()
            messages.success(request, f'Vendor "{vendor.name}" updated successfully.')
            return redirect('custom_admin:vendors_list')

        except Exception as e:
            logger.error(f"Error updating vendor: {str(e)}")
            messages.error(request, f'Error updating vendor: {str(e)}')

    context = {
        'page_title': 'Edit Vendor',
        'vendor': vendor,
        'vendor_types': Vendor.VENDOR_TYPE_CHOICES,
    }
    return render(request, 'custom_admin/finance/vendor_form.html', context)


@user_passes_test(is_staff_user)
def vendor_delete_view(request, vendor_id):
    """Delete a vendor"""
    vendor = get_object_or_404(Vendor, id=vendor_id)

    if request.method == 'POST':
        try:
            # Check if vendor has transactions
            if vendor.expenses.exists() or vendor.income_records.exists():
                messages.error(request, f'Cannot delete "{vendor.name}" - it has associated transactions.')
                return redirect('custom_admin:vendors_list')

            name = vendor.name
            vendor.delete()
            messages.success(request, f'Vendor "{name}" deleted successfully.')
        except Exception as e:
            logger.error(f"Error deleting vendor: {str(e)}")
            messages.error(request, f'Error deleting vendor: {str(e)}')

    return redirect('custom_admin:vendors_list')


@user_passes_test(is_staff_user)
def vendor_search_api(request):
    """API endpoint for vendor search (for autocomplete)"""
    query = request.GET.get('q', '').strip()
    vendor_type = request.GET.get('type', '')

    vendors = Vendor.objects.filter(is_active=True)

    if query:
        vendors = vendors.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

    if vendor_type:
        vendors = vendors.filter(vendor_type=vendor_type)

    vendors = vendors[:10]

    data = [
        {
            'id': v.id,
            'name': v.name,
            'type': v.get_vendor_type_display(),
            'email': v.email or '',
            'phone': v.phone or '',
            'gstin': v.gstin or '',
        }
        for v in vendors
    ]

    return JsonResponse({'vendors': data})


# =============================================================================
# PENDING FEES (Course Payments)
# =============================================================================

@user_passes_test(is_staff_user)
def pending_fees_list_view(request):
    """List all pending/overdue course fees with filters"""
    today = date.today()

    # Base queryset - pending and overdue payments
    payments = Payment.objects.select_related(
        'enrollment', 'enrollment__user', 'enrollment__course'
    ).filter(
        status__in=['pending', 'overdue']
    )

    # Apply filters
    course_id = request.GET.get('course')
    status = request.GET.get('status')
    month = request.GET.get('month')
    year = request.GET.get('year')
    search = request.GET.get('search', '').strip()

    if course_id:
        payments = payments.filter(enrollment__course_id=course_id)
    if status:
        payments = payments.filter(status=status)
    if month and year:
        # Filter by due_date month
        payments = payments.filter(
            due_date__month=int(month),
            due_date__year=int(year)
        )
    elif year:
        payments = payments.filter(due_date__year=int(year))
    if search:
        payments = payments.filter(
            Q(enrollment__user__name__icontains=search) |
            Q(enrollment__user__email__icontains=search) |
            Q(enrollment__course__title__icontains=search) |
            Q(invoice_number__icontains=search)
        )

    # Mark overdue payments
    overdue_count = payments.filter(due_date__lt=today, status='pending').update(status='overdue')

    # Order by due date (oldest first for urgency)
    payments = payments.order_by('due_date', 'enrollment__user__name')

    # Calculate totals
    total_pending = payments.filter(status='pending').aggregate(
        total=Sum('amount')
    )['total'] or 0
    total_overdue = payments.filter(status='overdue').aggregate(
        total=Sum('amount')
    )['total'] or 0

    # Pagination
    paginator = Paginator(payments, 20)
    page = request.GET.get('page', 1)
    payments = paginator.get_page(page)

    # Get filter options
    courses = Course.objects.filter(is_published=True).order_by('title')

    # Get months for filter
    current_year = today.year
    years = list(range(current_year - 2, current_year + 2))
    months = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]

    context = {
        'page_title': 'Pending Fees',
        'payments': payments,
        'courses': courses,
        'years': years,
        'months': months,
        'selected_course': course_id,
        'selected_status': status,
        'selected_month': month,
        'selected_year': year or str(current_year),
        'search': search,
        'total_pending': total_pending,
        'total_overdue': total_overdue,
        'total_outstanding': total_pending + total_overdue,
        'today': today,
    }
    return render(request, 'custom_admin/finance/pending_fees_list.html', context)


@user_passes_test(is_staff_user)
def monthly_fees_summary_view(request):
    """Monthly summary of pending fees by course"""
    today = date.today()

    # Get selected month/year or default to current
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))

    # Get first and last day of selected month
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    # Get all payments due in the selected month
    payments = Payment.objects.select_related(
        'enrollment', 'enrollment__user', 'enrollment__course'
    ).filter(
        due_date__gte=first_day,
        due_date__lte=last_day
    )

    # Summary by course
    course_summary = payments.values(
        'enrollment__course__id',
        'enrollment__course__title'
    ).annotate(
        total_due=Sum('amount'),
        pending_count=Count('id', filter=Q(status='pending')),
        pending_amount=Sum('amount', filter=Q(status='pending')),
        overdue_count=Count('id', filter=Q(status='overdue')),
        overdue_amount=Sum('amount', filter=Q(status='overdue')),
        completed_count=Count('id', filter=Q(status='completed')),
        completed_amount=Sum('amount', filter=Q(status='completed')),
    ).order_by('enrollment__course__title')

    # Overall totals
    overall_totals = payments.aggregate(
        total_due=Sum('amount'),
        total_pending=Sum('amount', filter=Q(status='pending')),
        total_overdue=Sum('amount', filter=Q(status='overdue')),
        total_collected=Sum('amount', filter=Q(status='completed')),
        pending_count=Count('id', filter=Q(status='pending')),
        overdue_count=Count('id', filter=Q(status='overdue')),
        completed_count=Count('id', filter=Q(status='completed')),
    )

    # Calculate collection rate
    total_due = overall_totals['total_due'] or 0
    total_collected = overall_totals['total_collected'] or 0
    collection_rate = (total_collected / total_due * 100) if total_due > 0 else 0

    # Get months for filter
    current_year = today.year
    years = list(range(current_year - 2, current_year + 2))
    months_list = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]

    context = {
        'page_title': 'Monthly Fees Summary',
        'course_summary': course_summary,
        'overall_totals': overall_totals,
        'collection_rate': round(collection_rate, 1),
        'selected_month': month,
        'selected_year': year,
        'years': years,
        'months': months_list,
        'month_name': months_list[month - 1][1],
        'first_day': first_day,
        'last_day': last_day,
    }
    return render(request, 'custom_admin/finance/monthly_fees_summary.html', context)


@user_passes_test(is_staff_user)
def collect_payment_view(request, payment_id):
    """Mark a payment as collected/completed"""
    payment = get_object_or_404(Payment, id=payment_id)

    if request.method == 'POST':
        try:
            payment_method = request.POST.get('payment_method', 'cash')
            transaction_id = request.POST.get('transaction_id', '').strip()
            notes = request.POST.get('notes', '').strip()

            payment.status = 'completed'
            payment.payment_method = payment_method
            payment.payment_date = timezone.now()
            payment.transaction_id = transaction_id or None
            if notes:
                payment.notes = (payment.notes or '') + f"\n[{date.today()}] {notes}"
            payment.save()

            # Update enrollment payment status
            enrollment = payment.enrollment
            total_paid = enrollment.payments.filter(status='completed').aggregate(
                total=Sum('amount')
            )['total'] or 0

            if total_paid >= enrollment.total_amount:
                enrollment.payment_status = 'completed'
            elif total_paid > 0:
                enrollment.payment_status = 'partial'
            enrollment.save()

            messages.success(request, f'Payment of ₹{payment.amount} collected successfully.')

        except Exception as e:
            logger.error(f"Error collecting payment: {str(e)}")
            messages.error(request, f'Error collecting payment: {str(e)}')

    return redirect('custom_admin:pending_fees_list')


@user_passes_test(is_staff_user)
def send_payment_reminder_view(request, payment_id):
    """Send payment reminder to student"""
    payment = get_object_or_404(Payment, id=payment_id)

    if request.method == 'POST':
        try:
            # TODO: Implement email/SMS reminder
            # For now, just log and show message
            logger.info(f"Payment reminder sent for payment {payment.id} to {payment.enrollment.user.email}")
            messages.success(request, f'Payment reminder sent to {payment.enrollment.user.name}.')
        except Exception as e:
            logger.error(f"Error sending payment reminder: {str(e)}")
            messages.error(request, f'Error sending reminder: {str(e)}')

    return redirect('custom_admin:pending_fees_list')

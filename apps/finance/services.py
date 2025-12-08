from django.db import transaction
from django.utils import timezone
from decimal import Decimal


def seed_default_categories():
    """Seed default expense and income categories"""
    from .models import ExpenseCategory, IncomeCategory

    # Default Expense Categories
    expense_categories = [
        {'name': 'Salaries & Wages', 'slug': 'salaries-wages', 'category_type': 'fixed', 'icon': 'ti-users', 'color': '#5d87ff', 'order': 1},
        {'name': 'Rent & Utilities', 'slug': 'rent-utilities', 'category_type': 'fixed', 'icon': 'ti-building', 'color': '#49beff', 'order': 2},
        {'name': 'Marketing & Advertising', 'slug': 'marketing-advertising', 'category_type': 'variable', 'icon': 'ti-speakerphone', 'color': '#fa896b', 'order': 3},
        {'name': 'Infrastructure & Equipment', 'slug': 'infrastructure-equipment', 'category_type': 'one_time', 'icon': 'ti-device-desktop', 'color': '#ffae1f', 'order': 4},
        {'name': 'Software & Subscriptions', 'slug': 'software-subscriptions', 'category_type': 'fixed', 'icon': 'ti-apps', 'color': '#13deb9', 'order': 5},
        {'name': 'Office Supplies', 'slug': 'office-supplies', 'category_type': 'variable', 'icon': 'ti-clipboard', 'color': '#539bff', 'order': 6},
        {'name': 'Travel & Transportation', 'slug': 'travel-transportation', 'category_type': 'variable', 'icon': 'ti-car', 'color': '#8b5cf6', 'order': 7},
        {'name': 'Professional Services', 'slug': 'professional-services', 'category_type': 'variable', 'icon': 'ti-briefcase', 'color': '#ef4444', 'order': 8},
        {'name': 'Training & Development', 'slug': 'training-development', 'category_type': 'variable', 'icon': 'ti-school', 'color': '#22c55e', 'order': 9},
        {'name': 'Miscellaneous', 'slug': 'miscellaneous', 'category_type': 'variable', 'icon': 'ti-dots', 'color': '#6b7280', 'order': 10},
    ]

    # Default Income Categories
    income_categories = [
        {'name': 'Course Fees', 'slug': 'course-fees', 'source_type': 'enrollment', 'is_auto_imported': True, 'icon': 'ti-book', 'color': '#13deb9', 'order': 1},
        {'name': 'Workshop Fees', 'slug': 'workshop-fees', 'source_type': 'event', 'icon': 'ti-calendar-event', 'color': '#5d87ff', 'order': 2},
        {'name': 'Event Registrations', 'slug': 'event-registrations', 'source_type': 'event', 'icon': 'ti-ticket', 'color': '#49beff', 'order': 3},
        {'name': 'Sponsorship Revenue', 'slug': 'sponsorship-revenue', 'source_type': 'sponsorship', 'icon': 'ti-award', 'color': '#ffae1f', 'order': 4},
        {'name': 'Corporate Training', 'slug': 'corporate-training', 'source_type': 'partnership', 'icon': 'ti-building-skyscraper', 'color': '#fa896b', 'order': 5},
        {'name': 'Consultation Fees', 'slug': 'consultation-fees', 'source_type': 'other', 'icon': 'ti-message-dots', 'color': '#8b5cf6', 'order': 6},
        {'name': 'Other Income', 'slug': 'other-income', 'source_type': 'other', 'icon': 'ti-wallet', 'color': '#6b7280', 'order': 7},
    ]

    created_expense = 0
    created_income = 0

    with transaction.atomic():
        for cat_data in expense_categories:
            obj, created = ExpenseCategory.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            if created:
                created_expense += 1

        for cat_data in income_categories:
            obj, created = IncomeCategory.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            if created:
                created_income += 1

    return created_expense, created_income


def sync_enrollment_payments():
    """
    Synchronize completed payments from Enrollment system to Finance Income.
    This imports completed course payments as income records.
    """
    from apps.payments.models import Payment
    from .models import Income, IncomeCategory

    # Get the Course Fees category
    try:
        course_fees_category = IncomeCategory.objects.get(slug='course-fees')
    except IncomeCategory.DoesNotExist:
        # Create it if it doesn't exist
        course_fees_category = IncomeCategory.objects.create(
            name='Course Fees',
            slug='course-fees',
            source_type='enrollment',
            is_auto_imported=True,
            icon='ti-book',
            color='#13deb9',
            order=1
        )

    # Get IDs of payments already imported
    synced_payment_ids = Income.objects.filter(
        is_auto_imported=True,
        payment__isnull=False
    ).values_list('payment_id', flat=True)

    # Get new completed payments
    new_payments = Payment.objects.filter(
        status='completed'
    ).exclude(
        id__in=synced_payment_ids
    ).select_related('enrollment__user', 'enrollment__course')

    created_count = 0
    for payment in new_payments:
        if payment.enrollment:
            enrollment = payment.enrollment
            user = enrollment.user
            course = enrollment.course

            Income.objects.create(
                title=f"Course Fee: {course.title}",
                description=f"Payment from {user.name} for course enrollment",
                category=course_fees_category,
                amount=payment.amount - (payment.tax_amount or Decimal('0.00')),
                tax_amount=payment.tax_amount or Decimal('0.00'),
                payment_method=payment.payment_method,
                payment_reference=payment.transaction_id or payment.razorpay_payment_id or '',
                payer_name=user.name,
                payer_email=user.email,
                payer_phone=getattr(user, 'phone_number', ''),
                invoice_number=payment.invoice_number,
                status='received',
                income_date=payment.payment_date.date() if payment.payment_date else timezone.now().date(),
                enrollment=enrollment,
                payment=payment,
                is_auto_imported=True
            )
            created_count += 1

    return created_count


def get_financial_summary(start_date, end_date):
    """
    Calculate financial summary for a given date range.
    Returns a dictionary with all KPIs.
    """
    from django.db.models import Sum, Count
    from .models import Income, Expense

    # Income calculations
    income_data = Income.objects.filter(
        income_date__gte=start_date,
        income_date__lte=end_date,
        status='received'
    ).aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )

    # Expense calculations
    expense_data = Expense.objects.filter(
        expense_date__gte=start_date,
        expense_date__lte=end_date,
        status='paid'
    ).aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )

    total_income = income_data['total'] or Decimal('0.00')
    total_expense = expense_data['total'] or Decimal('0.00')
    net_profit = total_income - total_expense

    # Calculate percentages
    profit_margin = Decimal('0.00')
    expense_ratio = Decimal('0.00')
    if total_income > 0:
        profit_margin = (net_profit / total_income) * 100
        expense_ratio = (total_expense / total_income) * 100

    return {
        'total_income': total_income,
        'total_expense': total_expense,
        'net_profit': net_profit,
        'profit_margin': round(profit_margin, 2),
        'expense_ratio': round(expense_ratio, 2),
        'income_count': income_data['count'] or 0,
        'expense_count': expense_data['count'] or 0,
    }


def get_category_breakdown(start_date, end_date):
    """
    Get income and expense breakdown by category for charts.
    """
    from django.db.models import Sum
    from .models import Income, Expense

    # Income by category
    income_by_category = Income.objects.filter(
        income_date__gte=start_date,
        income_date__lte=end_date,
        status='received'
    ).values('category__name', 'category__color').annotate(
        total=Sum('total_amount')
    ).order_by('-total')

    # Expense by category
    expense_by_category = Expense.objects.filter(
        expense_date__gte=start_date,
        expense_date__lte=end_date,
        status='paid'
    ).values('category__name', 'category__color').annotate(
        total=Sum('total_amount')
    ).order_by('-total')

    return {
        'income_by_category': list(income_by_category),
        'expense_by_category': list(expense_by_category),
    }


def get_monthly_trend(months=12):
    """
    Get monthly income and expense data for trend chart.
    """
    from django.db.models import Sum
    from django.db.models.functions import TruncMonth
    from .models import Income, Expense
    from datetime import date
    from dateutil.relativedelta import relativedelta

    end_date = date.today()
    start_date = end_date - relativedelta(months=months-1)
    start_date = start_date.replace(day=1)

    # Monthly income
    monthly_income = Income.objects.filter(
        income_date__gte=start_date,
        income_date__lte=end_date,
        status='received'
    ).annotate(
        month=TruncMonth('income_date')
    ).values('month').annotate(
        total=Sum('total_amount')
    ).order_by('month')

    # Monthly expenses
    monthly_expense = Expense.objects.filter(
        expense_date__gte=start_date,
        expense_date__lte=end_date,
        status='paid'
    ).annotate(
        month=TruncMonth('expense_date')
    ).values('month').annotate(
        total=Sum('total_amount')
    ).order_by('month')

    # Convert to dict for easy lookup
    income_dict = {item['month']: float(item['total']) for item in monthly_income}
    expense_dict = {item['month']: float(item['total']) for item in monthly_expense}

    # Generate all months
    months_list = []
    income_data = []
    expense_data = []
    current = start_date
    while current <= end_date:
        month_date = current.replace(day=1)
        months_list.append(current.strftime('%b %Y'))
        income_data.append(income_dict.get(month_date, 0))
        expense_data.append(expense_dict.get(month_date, 0))
        current = current + relativedelta(months=1)

    return {
        'labels': months_list,
        'income': income_data,
        'expense': expense_data,
    }

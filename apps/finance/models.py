from django.db import models
from django.conf import settings
from django.utils.text import slugify
from decimal import Decimal


class Vendor(models.Model):
    """Vendors/Payers for expenses and income - saved for quick reuse"""

    VENDOR_TYPE_CHOICES = [
        ('supplier', 'Supplier/Vendor'),
        ('service_provider', 'Service Provider'),
        ('employee', 'Employee'),
        ('customer', 'Customer/Payer'),
        ('partner', 'Partner/Sponsor'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    vendor_type = models.CharField(max_length=20, choices=VENDOR_TYPE_CHOICES, default='supplier')
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gstin = models.CharField(max_length=20, blank=True, null=True, help_text="GST Number")
    pan = models.CharField(max_length=15, blank=True, null=True, help_text="PAN Number")
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_account = models.CharField(max_length=50, blank=True, null=True)
    bank_ifsc = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'finance_vendors'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_vendor_type_display()})"


class ExpenseCategory(models.Model):
    """Predefined categories for institutional expenses"""

    CATEGORY_TYPE_CHOICES = [
        ('fixed', 'Fixed Cost'),
        ('variable', 'Variable Cost'),
        ('one_time', 'One-Time'),
    ]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, default='ti-folder', help_text="Tabler icon class")
    color = models.CharField(max_length=20, default='#5d87ff', help_text="Hex color for UI")
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPE_CHOICES, default='variable')
    is_active = models.BooleanField(default=True)
    budget_limit = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text="Monthly budget limit for this category"
    )
    order = models.PositiveIntegerField(default=0, help_text="Display order")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'finance_expense_categories'
        ordering = ['order', 'name']
        verbose_name_plural = 'Expense Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Expense(models.Model):
    """Individual expense records for the institution"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('upi', 'UPI'),
        ('cheque', 'Cheque'),
        ('other', 'Other'),
    ]

    RECURRING_CHOICES = [
        ('none', 'Non-Recurring'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    # Basic Information
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses'
    )

    # Financial Details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    currency = models.CharField(max_length=3, default='INR')

    # Payment Details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='bank_transfer')
    payment_reference = models.CharField(max_length=100, blank=True, null=True, help_text="Transaction ID or reference number")
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='expenses',
        help_text="Select from saved vendors"
    )
    vendor_name = models.CharField(max_length=200, blank=True, null=True, help_text="Or enter vendor name manually")
    vendor_gstin = models.CharField(max_length=20, blank=True, null=True, help_text="GST Number")
    invoice_number = models.CharField(max_length=50, blank=True, null=True)

    # Status & Dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    expense_date = models.DateField(help_text="Date when expense was incurred")
    payment_date = models.DateField(null=True, blank=True, help_text="Date when payment was made")
    due_date = models.DateField(null=True, blank=True)

    # Recurring
    is_recurring = models.CharField(max_length=20, choices=RECURRING_CHOICES, default='none')
    recurring_end_date = models.DateField(null=True, blank=True)
    parent_expense = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='recurring_instances'
    )

    # Attachments
    receipt = models.FileField(upload_to='finance/receipts/%Y/%m/', blank=True, null=True)
    invoice_file = models.FileField(upload_to='finance/invoices/%Y/%m/', blank=True, null=True)

    # Audit Trail
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_expenses'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_expenses'
    )
    notes = models.TextField(blank=True, null=True, help_text="Internal notes")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'finance_expenses'
        ordering = ['-expense_date', '-created_at']
        indexes = [
            models.Index(fields=['expense_date']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
            models.Index(fields=['is_recurring']),
        ]

    def save(self, *args, **kwargs):
        self.total_amount = self.amount + self.tax_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.total_amount} ({self.expense_date})"


class IncomeCategory(models.Model):
    """Predefined categories for institutional income"""

    SOURCE_TYPE_CHOICES = [
        ('enrollment', 'Course Enrollment'),
        ('event', 'Event/Workshop'),
        ('sponsorship', 'Sponsorship'),
        ('partnership', 'Partnership'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, default='ti-wallet', help_text="Tabler icon class")
    color = models.CharField(max_length=20, default='#2ab673', help_text="Hex color for UI")
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES, default='other')
    is_auto_imported = models.BooleanField(
        default=False,
        help_text="Income is automatically imported from payments system"
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'finance_income_categories'
        ordering = ['order', 'name']
        verbose_name_plural = 'Income Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Income(models.Model):
    """Individual income records for the institution"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('received', 'Received'),
        ('partial', 'Partially Received'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('cheque', 'Cheque'),
        ('other', 'Other'),
    ]

    # Basic Information
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        IncomeCategory,
        on_delete=models.PROTECT,
        related_name='incomes'
    )

    # Financial Details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    currency = models.CharField(max_length=3, default='INR')

    # Payment Details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    payer = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='income_records',
        help_text="Select from saved payers/customers"
    )
    payer_name = models.CharField(max_length=200, blank=True, null=True, help_text="Or enter payer name manually")
    payer_email = models.EmailField(blank=True, null=True)
    payer_phone = models.CharField(max_length=20, blank=True, null=True)
    invoice_number = models.CharField(max_length=50, blank=True, null=True)

    # Status & Dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    income_date = models.DateField(help_text="Date when income was received/expected")

    # Link to Enrollment Payment (for auto-imported income)
    enrollment = models.ForeignKey(
        'payments.Enrollment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='finance_income_records'
    )
    payment = models.ForeignKey(
        'payments.Payment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='finance_income_records'
    )
    is_auto_imported = models.BooleanField(default=False)

    # Attachments
    receipt = models.FileField(upload_to='finance/income_receipts/%Y/%m/', blank=True, null=True)

    # Audit Trail
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_incomes'
    )
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'finance_incomes'
        ordering = ['-income_date', '-created_at']
        indexes = [
            models.Index(fields=['income_date']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
            models.Index(fields=['is_auto_imported']),
            models.Index(fields=['payment']),
        ]

    def save(self, *args, **kwargs):
        self.total_amount = self.amount + self.tax_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.total_amount} ({self.income_date})"


class FinancialSummary(models.Model):
    """Cached financial summaries for performance optimization"""

    SUMMARY_TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    summary_type = models.CharField(max_length=20, choices=SUMMARY_TYPE_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()

    # Income Summary
    total_income = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    enrollment_income = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    other_income = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    income_count = models.PositiveIntegerField(default=0)

    # Expense Summary
    total_expense = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    expense_count = models.PositiveIntegerField(default=0)

    # Category-wise breakdown (stored as JSON)
    income_by_category = models.JSONField(default=dict)
    expense_by_category = models.JSONField(default=dict)

    # Derived Metrics
    net_profit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    expense_ratio = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    # Comparison metrics (percentage change from previous period)
    income_growth = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    expense_growth = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    last_calculated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'finance_summaries'
        unique_together = ['summary_type', 'period_start', 'period_end']
        ordering = ['-period_start']

    def __str__(self):
        return f"{self.get_summary_type_display()} Summary: {self.period_start} to {self.period_end}"

    def calculate_metrics(self):
        """Calculate derived metrics"""
        self.net_profit = self.total_income - self.total_expense
        if self.total_income > 0:
            self.profit_margin = (self.net_profit / self.total_income) * 100
            self.expense_ratio = (self.total_expense / self.total_income) * 100
        else:
            self.profit_margin = Decimal('0.00')
            self.expense_ratio = Decimal('0.00')

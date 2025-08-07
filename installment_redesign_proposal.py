# Proposed Model Structure for Installment Plans

from django.db import models
from django.conf import settings

class InstallmentPlanTemplate(models.Model):
    """Reusable installment plan templates"""
    FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('weekly', 'Weekly'),
        ('quarterly', 'Quarterly'),
        ('custom', 'Custom'),
    ]
    
    # Plan identification
    name = models.CharField(max_length=100, help_text="Plan name (e.g., '3-Month Plan', 'Student Plan')")
    description = models.TextField(blank=True, help_text="Plan description")
    
    # Plan configuration
    total_installments = models.PositiveIntegerField(help_text="Number of installments")
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='monthly')
    
    # Pricing structure (percentage-based for flexibility)
    down_payment_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        help_text="Percentage of total amount as down payment (0-100)"
    )
    installment_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Percentage per installment of remaining amount"
    )
    
    # Plan settings
    is_active = models.BooleanField(default=True)
    applies_to_courses = models.ManyToManyField('courses.Course', blank=True, 
                                             help_text="If empty, applies to all courses")
    minimum_course_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Minimum course price to use this plan"
    )
    
    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.total_installments} installments)"
    
    def calculate_installment_amount(self, total_course_price):
        """Calculate installment amount for given course price"""
        down_payment = total_course_price * (self.down_payment_percentage / 100)
        remaining_amount = total_course_price - down_payment
        installment_amount = remaining_amount / self.total_installments
        return {
            'down_payment': down_payment,
            'installment_amount': installment_amount,
            'total_amount': total_course_price
        }
    
    def is_applicable_to_course(self, course):
        """Check if this plan can be used for given course"""
        if not self.is_active:
            return False
        if course.total_price < self.minimum_course_price:
            return False
        if self.applies_to_courses.exists() and course not in self.applies_to_courses.all():
            return False
        return True
    
    class Meta:
        db_table = 'installment_plan_templates'


class Enrollment(models.Model):
    # ... existing fields ...
    
    # Replace the OneToOne relationship with ForeignKey to template
    installment_plan_template = models.ForeignKey(
        'InstallmentPlanTemplate', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        help_text="Installment plan template for this enrollment"
    )
    
    # Store the actual calculated amounts for this enrollment
    down_payment_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Calculated down payment for this enrollment"
    )
    installment_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Calculated installment amount for this enrollment"
    )
    
    @property
    def has_installment_plan(self):
        return self.installment_plan_template is not None
    
    def calculate_payment_schedule(self):
        """Generate payment schedule based on template"""
        if not self.installment_plan_template:
            return []
        
        template = self.installment_plan_template
        amounts = template.calculate_installment_amount(self.total_amount)
        
        schedule = []
        from datetime import date, timedelta
        
        # Add down payment if applicable
        if amounts['down_payment'] > 0:
            schedule.append({
                'installment_number': 0,  # 0 for down payment
                'amount': amounts['down_payment'],
                'due_date': date.today(),
                'type': 'down_payment'
            })
        
        # Add regular installments
        start_date = date.today()
        if template.frequency == 'monthly':
            delta_days = 30
        elif template.frequency == 'weekly':
            delta_days = 7
        elif template.frequency == 'quarterly':
            delta_days = 90
        else:
            delta_days = 30  # Default to monthly
        
        for i in range(template.total_installments):
            due_date = start_date + timedelta(days=delta_days * (i + 1))
            schedule.append({
                'installment_number': i + 1,
                'amount': amounts['installment_amount'],
                'due_date': due_date,
                'type': 'installment'
            })
        
        return schedule


# Remove the old InstallmentPlan model or rename it to InstallmentPlanInstance
# if you want to keep historical records


class Payment(models.Model):
    # ... existing fields ...
    
    # Add reference to which template was used (for historical tracking)
    installment_plan_template = models.ForeignKey(
        'InstallmentPlanTemplate',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Plan template used for this payment"
    )


# Example Plan Templates You Could Create:

"""
1. "Standard 3-Month Plan"
   - 3 installments
   - Monthly frequency
   - 0% down payment
   - 33.33% per installment

2. "Premium 6-Month Plan"  
   - 6 installments
   - Monthly frequency
   - 20% down payment
   - 13.33% per installment

3. "Student Budget Plan"
   - 12 installments  
   - Monthly frequency
   - 10% down payment
   - 7.5% per installment
   - Only for courses > ₹15,000

4. "Corporate Quick Plan"
   - 2 installments
   - Monthly frequency  
   - 50% down payment
   - 25% per installment
"""
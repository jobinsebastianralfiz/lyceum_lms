from django.core.management.base import BaseCommand
from emails.models import EmailTemplate


class Command(BaseCommand):
    help = 'Create default email templates for the application'

    def handle(self, *args, **options):
        templates = [
            {
                'name': 'Email Verification Template',
                'template_type': 'verification',
                'subject': 'Verify Your Email - {{ site_name }}',
                'html_content': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8fffe;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(189, 208, 202, 0.2);
        }
        .header {
            background: linear-gradient(135deg, #BDD0CA, #2C5F5F);
            padding: 40px 20px;
            text-align: center;
            color: white;
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
            font-weight: 700;
        }
        .header p {
            font-size: 16px;
            opacity: 0.9;
        }
        .content {
            padding: 40px 30px;
        }
        .welcome-text {
            font-size: 18px;
            margin-bottom: 25px;
            color: #2C3E50;
        }
        .verification-section {
            background: #f8fffe;
            border-radius: 15px;
            padding: 30px;
            text-align: center;
            margin: 30px 0;
            border: 1px solid rgba(189, 208, 202, 0.3);
        }
        .verify-btn {
            display: inline-block;
            background: linear-gradient(135deg, #2C5F5F, #BDD0CA);
            color: white;
            padding: 18px 40px;
            text-decoration: none;
            border-radius: 12px;
            font-weight: 600;
            font-size: 16px;
            margin: 20px 0;
            transition: transform 0.3s ease;
        }
        .verify-btn:hover {
            transform: translateY(-2px);
            text-decoration: none;
            color: white;
        }
        .verification-link {
            background: #f1f3f4;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            word-break: break-all;
            font-size: 14px;
            color: #666;
        }
        .footer {
            background: #2C5F5F;
            color: white;
            padding: 30px;
            text-align: center;
        }
        .footer p {
            margin: 5px 0;
            opacity: 0.9;
        }
        .footer a {
            color: #BDD0CA;
            text-decoration: none;
        }
        .icon {
            font-size: 48px;
            margin-bottom: 20px;
        }
        .warning {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="icon" style="font-size: 48px; margin-bottom: 20px;">*</div>
            <h1>Welcome to {{ site_name }}!</h1>
            <p>Your learning journey starts here</p>
        </div>
        
        <div class="content">
            <p class="welcome-text">Hi {{ user.name }},</p>
            
            <p>Thank you for registering with {{ site_name }}! We're excited to have you join our community of learners.</p>
            
            <div class="verification-section">
                <h2 style="color: #2C5F5F; margin-bottom: 15px;">Verify Your Email Address</h2>
                <p>To complete your registration and start learning, please verify your email address by clicking the button below:</p>
                
                <a href="{{ verification_url }}" class="verify-btn">
                    Verify Email Address
                </a>
                
                <p style="margin-top: 20px; font-size: 14px; color: #666;">
                    Can't click the button? Copy and paste this link into your browser:
                </p>
                <div class="verification-link">
                    {{ verification_url }}
                </div>
            </div>
            
            <div class="warning">
                <strong>Important:</strong> This verification link will expire in {{ expires_hours }} hours for security reasons.
            </div>
            
            <p>Once your email is verified, you'll be able to:</p>
            <ul style="margin: 15px 0; padding-left: 20px; color: #2C3E50;">
                <li>Access your student dashboard</li>
                <li>Enroll in courses</li>
                <li>Track your learning progress</li>
                <li>Receive important updates</li>
            </ul>
            
            <p>If you didn't create this account, you can safely ignore this email.</p>
        </div>
        
        <div class="footer">
            <p><strong>{{ site_name }} Team</strong></p>
            <p>Need help? Contact us at <a href="mailto:{{ support_email }}">{{ support_email }}</a></p>
            <p style="font-size: 12px; margin-top: 15px; opacity: 0.7;">
                This email was sent to {{ user.email }}. Please do not reply to this email.
            </p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Hi {{ user.name }},

Welcome to {{ site_name }}!

Thank you for registering with us. To complete your registration, please verify your email address by visiting this link:

{{ verification_url }}

This link will expire in {{ expires_hours }} hours.

If you didn't create this account, you can safely ignore this email.

Best regards,
{{ site_name }} Team

Need help? Contact us at {{ support_email }}
                '''
            },
            {
                'name': 'Tax Invoice Email Template',
                'template_type': 'invoice',
                'subject': 'Tax Invoice for {{ course.title }} - {{ site_name }}',
                'html_content': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tax Invoice</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8fffe;
        }
        .container {
            max-width: 700px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(189, 208, 202, 0.2);
        }
        .header {
            background: linear-gradient(135deg, #2C5F5F, #BDD0CA);
            padding: 40px 30px;
            color: white;
            text-align: center;
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        .content {
            padding: 40px 30px;
        }
        .invoice-details {
            background: #f8fffe;
            border-radius: 15px;
            padding: 25px;
            margin: 25px 0;
            border: 1px solid rgba(189, 208, 202, 0.3);
        }
        .detail-row {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        .detail-row:last-child {
            border-bottom: none;
            font-weight: bold;
            font-size: 18px;
            color: #2C5F5F;
        }
        .attachment-notice {
            background: #e3f2fd;
            border: 1px solid #90caf9;
            padding: 20px;
            border-radius: 12px;
            margin: 25px 0;
            text-align: center;
            color: #1565c0;
        }
        .footer {
            background: #2C5F5F;
            color: white;
            padding: 30px;
            text-align: center;
        }
        .footer a {
            color: #BDD0CA;
            text-decoration: none;
        }
        .thank-you {
            background: linear-gradient(135deg, rgba(189, 208, 202, 0.1), rgba(44, 95, 95, 0.1));
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            margin: 25px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Tax Invoice</h1>
            <p>{{ site_name }}</p>
        </div>
        
        <div class="content">
            <p style="font-size: 18px; color: #2C3E50; margin-bottom: 20px;">
                Hi {{ user.name }},
            </p>
            
            <p>Thank you for your enrollment in <strong>{{ course.title }}</strong>!</p>
            
            <div class="invoice-details">
                <h3 style="color: #2C5F5F; margin-bottom: 20px;">Enrollment Details</h3>
                <div class="detail-row">
                    <span>Course:</span>
                    <span><strong>{{ course.title }}</strong></span>
                </div>
                <div class="detail-row">
                    <span>Student:</span>
                    <span>{{ user.name }}</span>
                </div>
                <div class="detail-row">
                    <span>Email:</span>
                    <span>{{ user.email }}</span>
                </div>
                <div class="detail-row">
                    <span>Enrolled On:</span>
                    <span>{{ enrollment.enrolled_on|date:"F d, Y" }}</span>
                </div>
                <div class="detail-row">
                    <span>Payment Status:</span>
                    <span style="color: #28a745;">{{ enrollment.payment_status|title }}</span>
                </div>
                <div class="detail-row">
                    <span>Total Amount:</span>
                    <span>Rs.{{ enrollment.total_amount }}</span>
                </div>
            </div>
            
            <div class="attachment-notice">
                <h3 style="margin-bottom: 15px;">Tax Invoice Attached</h3>
                <p>Your official tax invoice is attached to this email as a PDF document. Please save it for your records and tax purposes.</p>
            </div>
            
            <div class="thank-you">
                <h3 style="color: #2C5F5F; margin-bottom: 15px;">Welcome to Your Learning Journey!</h3>
                <p>You can now access your course materials and start learning. Log in to your student portal to begin!</p>
                <a href="{{ student_portal_url }}" style="display: inline-block; background: #2C5F5F; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; margin-top: 15px;">
                    Access Student Portal
                </a>
            </div>
            
            <p style="margin-top: 25px;">If you have any questions about your enrollment or need assistance, please don't hesitate to contact us.</p>
        </div>
        
        <div class="footer">
            <p><strong>{{ site_name }} Team</strong></p>
            <p>Need help? Contact us at <a href="mailto:{{ support_email }}">{{ support_email }}</a></p>
            <p style="font-size: 12px; margin-top: 15px; opacity: 0.7;">
                This email was sent to {{ user.email }}
            </p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Tax Invoice - {{ site_name }}

Hi {{ user.name }},

Thank you for your enrollment in {{ course.title }}!

ENROLLMENT DETAILS:
- Course: {{ course.title }}
- Student: {{ user.name }}
- Email: {{ user.email }}
- Enrolled On: {{ enrollment.enrolled_on|date:"F d, Y" }}
- Payment Status: {{ enrollment.payment_status|title }}
- Total Amount: Rs.{{ enrollment.total_amount }}

Your official tax invoice is attached to this email as a PDF document. Please save it for your records and tax purposes.

Welcome to your learning journey! You can now access your course materials and start learning.

Best regards,
{{ site_name }} Team

Need help? Contact us at {{ support_email }}
                '''
            },
            {
                'name': 'Enrollment Confirmation Email Template',
                'template_type': 'enrollment_confirmation',
                'subject': 'Welcome to {{ course.title }} - {{ site_name }}',
                'html_content': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enrollment Confirmation</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8fffe;
        }
        .container {
            max-width: 700px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(189, 208, 202, 0.2);
        }
        .header {
            background: linear-gradient(135deg, #28a745, #20c997);
            padding: 40px 30px;
            color: white;
            text-align: center;
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        .content {
            padding: 40px 30px;
        }
        .welcome-section {
            background: #f8fffe;
            border-radius: 15px;
            padding: 25px;
            margin: 25px 0;
            border-left: 5px solid #28a745;
        }
        .course-details {
            background: #e8f5e8;
            border-radius: 15px;
            padding: 25px;
            margin: 25px 0;
            border: 1px solid rgba(40, 167, 69, 0.3);
        }
        .detail-row {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        .detail-row:last-child {
            border-bottom: none;
        }
        .cta-button {
            display: inline-block;
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            padding: 18px 40px;
            text-decoration: none;
            border-radius: 12px;
            font-weight: 600;
            font-size: 16px;
            margin: 20px auto;
            text-align: center;
            transition: transform 0.3s ease;
        }
        .cta-button:hover {
            transform: translateY(-2px);
            text-decoration: none;
            color: white;
        }
        .footer {
            background: #2C5F5F;
            color: white;
            padding: 30px;
            text-align: center;
        }
        .footer a {
            color: #BDD0CA;
            text-decoration: none;
        }
        .next-steps {
            background: linear-gradient(135deg, rgba(40, 167, 69, 0.1), rgba(32, 201, 151, 0.1));
            padding: 25px;
            border-radius: 15px;
            margin: 25px 0;
        }
        .celebration-icon {
            font-size: 48px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="celebration-icon">*</div>
            <h1>Enrollment Confirmed!</h1>
            <p>Welcome to {{ course.title }}</p>
        </div>
        
        <div class="content">
            <p style="font-size: 18px; color: #2C3E50; margin-bottom: 20px;">
                Hi {{ user.name }},
            </p>
            
            <div class="welcome-section">
                <h3 style="color: #28a745; margin-bottom: 15px;">> Welcome to Your Learning Journey!</h3>
                <p>Congratulations! You have successfully enrolled in <strong>{{ course.title }}</strong>. We're excited to have you join our community of learners!</p>
            </div>

            <div class="course-details">
                <h3 style="color: #2C5F5F; margin-bottom: 20px;">- Course Details</h3>
                <div class="detail-row">
                    <span><strong>Course:</strong></span>
                    <span>{{ course.title }}</span>
                </div>
                {% if course.description %}
                <div class="detail-row">
                    <span><strong>Description:</strong></span>
                    <span>{{ course.description|truncatechars:100 }}</span>
                </div>
                {% endif %}
                <div class="detail-row">
                    <span><strong>Enrolled On:</strong></span>
                    <span>{{ enrollment.enrolled_on|date:"F d, Y" }}</span>
                </div>
                <div class="detail-row">
                    <span><strong>Payment Status:</strong></span>
                    <span style="color: #28a745;"><strong>{{ enrollment.payment_status|title }}</strong></span>
                </div>
                {% if enrollment.total_amount > 0 %}
                <div class="detail-row">
                    <span><strong>Total Amount Paid:</strong></span>
                    <span><strong>Rs.{{ enrollment.total_amount }}</strong></span>
                </div>
                {% endif %}
            </div>
            
            <div class="next-steps">
                <h3 style="color: #2C5F5F; margin-bottom: 20px;">* What's Next?</h3>
                <ul style="padding-left: 20px; color: #2C3E50;">
                    <li style="margin: 10px 0;">Access your student dashboard to view course materials</li>
                    <li style="margin: 10px 0;">Start with the first lesson or module</li>
                    <li style="margin: 10px 0;">Track your progress and complete assignments</li>
                    <li style="margin: 10px 0;">Join our community discussions and forums</li>
                    <li style="margin: 10px 0;">Download your tax invoice (attached to this email)</li>
                </ul>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="{{ student_portal_url|default:'/student/' }}" class="cta-button">
                        > Start Learning Now
                    </a>
                </div>
            </div>
            
            <p style="margin-top: 25px;">If you have any questions or need assistance, don't hesitate to reach out to our support team. We're here to help you succeed!</p>
            
            <p style="margin-top: 20px; color: #666; font-style: italic;">Happy Learning! *</p>
        </div>
        
        <div class="footer">
            <p><strong>{{ site_name }} Team</strong></p>
            <p>Need help? Contact us at <a href="mailto:{{ support_email }}">{{ support_email }}</a></p>
            <p style="font-size: 12px; margin-top: 15px; opacity: 0.7;">
                This email was sent to {{ user.email }}
            </p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
ENROLLMENT CONFIRMED!

Hi {{ user.name }},

Congratulations! You have successfully enrolled in {{ course.title }}. We're excited to have you join our community of learners!

COURSE DETAILS:
- Course: {{ course.title }}
{% if course.description %}- Description: {{ course.description|truncatechars:100 }}{% endif %}
- Enrolled On: {{ enrollment.enrolled_on|date:"F d, Y" }}
- Payment Status: {{ enrollment.payment_status|title }}
{% if enrollment.total_amount > 0 %}- Total Amount Paid: Rs.{{ enrollment.total_amount }}{% endif %}

WHAT'S NEXT?
* Access your student dashboard to view course materials
* Start with the first lesson or module  
* Track your progress and complete assignments
* Join our community discussions and forums
* Download your tax invoice (attached to this email)

Ready to start learning? Visit: {{ student_portal_url|default:"/student/" }}

If you have any questions or need assistance, don't hesitate to reach out to our support team.

Happy Learning! *

Best regards,
{{ site_name }} Team

Need help? Contact us at {{ support_email }}
                '''
            }
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates:
            template, created = EmailTemplate.objects.get_or_create(
                template_type=template_data['template_type'],
                defaults=template_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template.name}')
                )
            else:
                # Update existing template
                for key, value in template_data.items():
                    if key != 'template_type':  # Don't update the unique key
                        setattr(template, key, value)
                template.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated template: {template.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Created {created_count} new templates, updated {updated_count} existing templates.'
            )
        )
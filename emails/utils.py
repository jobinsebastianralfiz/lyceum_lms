import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from django.conf import settings
from django.utils import timezone
from django.template import Template, Context
from django.contrib.auth import get_user_model
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64

from .models import EmailVerification, EmailTemplate, SentEmail

User = get_user_model()
logger = logging.getLogger(__name__)


class EmailService:
    """SendGrid email service for beautiful emails"""
    
    def __init__(self):
        self.sg = SendGridAPIClient(api_key=settings.EMAIL_HOST_PASSWORD)
        self.from_email = settings.DEFAULT_FROM_EMAIL
    
    def send_email(self, to_email: str, subject: str, html_content: str, 
                   text_content: str = "", to_name: str = "", 
                   template_type: str = "", user: User = None, 
                   enrollment=None, attachments: list = None) -> bool:
        """Send email via SendGrid with tracking"""
        
        try:
            # Create SendGrid mail object
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content,
                plain_text_content=text_content or self._html_to_text(html_content)
            )
            
            # Add attachments if any
            if attachments:
                for attachment_data in attachments:
                    attachment = Attachment(
                        FileContent(attachment_data['content']),
                        FileName(attachment_data['filename']),
                        FileType(attachment_data['type']),
                        Disposition('attachment')
                    )
                    message.attachment = attachment
            
            # Send email
            response = self.sg.send(message)
            
            # Create tracking record
            sent_email = SentEmail.objects.create(
                recipient_email=to_email,
                recipient_name=to_name,
                sender_email=self.from_email,
                subject=subject,
                template_type=template_type,
                sendgrid_message_id=response.headers.get('X-Message-Id', ''),
                status='sent' if response.status_code == 202 else 'failed',
                sent_at=timezone.now() if response.status_code == 202 else None,
                failed_reason='' if response.status_code == 202 else f"Status: {response.status_code}",
                user=user,
                enrollment=enrollment
            )
            
            if response.status_code == 202:
                logger.info(f"Email sent successfully to {to_email}: {subject}")
                return True
            else:
                logger.error(f"Email failed to send to {to_email}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Email sending error: {str(e)}")
            # Create failed tracking record
            SentEmail.objects.create(
                recipient_email=to_email,
                recipient_name=to_name,
                sender_email=self.from_email,
                subject=subject,
                template_type=template_type,
                status='failed',
                failed_reason=str(e),
                user=user,
                enrollment=enrollment
            )
            return False
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text for fallback"""
        import re
        # Simple HTML to text conversion
        text = re.sub(r'<[^>]+>', '', html_content)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def render_template(self, template_type: str, context: Dict[str, Any]) -> tuple:
        """Render email template with context"""
        try:
            template = EmailTemplate.objects.get(template_type=template_type, is_active=True)
            
            # Render subject
            subject_template = Template(template.subject)
            rendered_subject = subject_template.render(Context(context))
            
            # Render HTML content
            html_template = Template(template.html_content)
            rendered_html = html_template.render(Context(context))
            
            # Render text content if available
            rendered_text = ""
            if template.text_content:
                text_template = Template(template.text_content)
                rendered_text = text_template.render(Context(context))
            
            return rendered_subject, rendered_html, rendered_text
            
        except EmailTemplate.DoesNotExist:
            logger.error(f"Email template not found: {template_type}")
            raise ValueError(f"Email template not found: {template_type}")
    
    def send_verification_email(self, user: User) -> bool:
        """Send email verification email"""
        # Generate verification token
        token = str(uuid.uuid4())
        expires_at = timezone.now() + timedelta(hours=24)
        
        # Create or update verification record
        verification, created = EmailVerification.objects.get_or_create(
            user=user,
            defaults={
                'token': token,
                'expires_at': expires_at
            }
        )
        
        if not created:
            verification.token = token
            verification.expires_at = expires_at
            verification.is_verified = False
            verification.verified_at = None
            verification.save()
        
        # Prepare context
        verification_url = f"{settings.FRONTEND_URL or 'http://localhost:8000'}/verify-email/{token}/"
        context = {
            'user': user,
            'verification_url': verification_url,
            'expires_hours': 24,
            'site_name': 'UpTrail',
            'support_email': 'support@uptrail.com'
        }
        
        try:
            subject, html_content, text_content = self.render_template('verification', context)
            return self.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                to_name=user.name,
                template_type='verification',
                user=user
            )
        except ValueError as e:
            logger.error(f"Template error: {e}")
            # Fallback email if template doesn't exist
            return self._send_verification_fallback(user, verification_url)
    
    def _send_verification_fallback(self, user: User, verification_url: str) -> bool:
        """Fallback verification email if template doesn't exist"""
        subject = "Verify Your Email - UpTrail"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2C5F5F;">Welcome to UpTrail!</h2>
                <p>Hi {user.name},</p>
                <p>Thank you for registering with UpTrail. Please verify your email address by clicking the button below:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" style="background: #2C5F5F; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; display: inline-block;">
                        Verify Email Address
                    </a>
                </div>
                <p>Or copy and paste this link in your browser:</p>
                <p><a href="{verification_url}">{verification_url}</a></p>
                <p>This link will expire in 24 hours.</p>
                <p>Best regards,<br>The UpTrail Team</p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(
            to_email=user.email,
            subject=subject,
            html_content=html_content,
            to_name=user.name,
            template_type='verification',
            user=user
        )
    
    def send_invoice_email(self, enrollment, invoice_pdf_content: bytes) -> bool:
        """Send tax invoice email with PDF attachment"""
        context = {
            'user': enrollment.user,
            'enrollment': enrollment,
            'course': enrollment.course,
            'invoice': enrollment.tax_invoices.first(),
            'site_name': 'UpTrail',
            'support_email': 'support@uptrail.com'
        }
        
        # Prepare PDF attachment
        pdf_attachment = {
            'content': base64.b64encode(invoice_pdf_content).decode(),
            'filename': f'invoice_{enrollment.id}.pdf',
            'type': 'application/pdf'
        }
        
        try:
            subject, html_content, text_content = self.render_template('invoice', context)
            return self.send_email(
                to_email=enrollment.user.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                to_name=enrollment.user.name,
                template_type='invoice',
                user=enrollment.user,
                enrollment=enrollment,
                attachments=[pdf_attachment]
            )
        except ValueError as e:
            logger.error(f"Template error: {e}")
            # Fallback email if template doesn't exist
            return self._send_invoice_fallback(enrollment, pdf_attachment)
    
    def _send_invoice_fallback(self, enrollment, pdf_attachment: dict) -> bool:
        """Fallback invoice email if template doesn't exist"""
        subject = f"Tax Invoice for {enrollment.course.title} - UpTrail"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2C5F5F;">Tax Invoice</h2>
                <p>Hi {enrollment.user.name},</p>
                <p>Thank you for your enrollment in <strong>{enrollment.course.title}</strong>.</p>
                <p>Please find your tax invoice attached to this email.</p>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3>Enrollment Details:</h3>
                    <p><strong>Course:</strong> {enrollment.course.title}</p>
                    <p><strong>Amount:</strong> ₹{enrollment.total_amount}</p>
                    <p><strong>Payment Status:</strong> {enrollment.payment_status.title()}</p>
                    <p><strong>Enrolled On:</strong> {enrollment.enrolled_on.strftime('%B %d, %Y')}</p>
                </div>
                <p>If you have any questions, please contact our support team.</p>
                <p>Best regards,<br>The UpTrail Team</p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(
            to_email=enrollment.user.email,
            subject=subject,
            html_content=html_content,
            to_name=enrollment.user.name,
            template_type='invoice',
            user=enrollment.user,
            enrollment=enrollment,
            attachments=[pdf_attachment]
        )


# Convenience functions
def send_verification_email(user: User) -> bool:
    """Send verification email to user"""
    email_service = EmailService()
    return email_service.send_verification_email(user)


def send_invoice_email(enrollment, invoice_pdf_content: bytes) -> bool:
    """Send invoice email to user"""
    email_service = EmailService()
    return email_service.send_invoice_email(enrollment, invoice_pdf_content)


def verify_email_token(token: str) -> tuple[bool, str]:
    """Verify email token and activate user"""
    try:
        verification = EmailVerification.objects.get(token=token)
        
        if verification.is_expired:
            return False, "Verification link has expired. Please request a new one."
        
        if verification.is_verified:
            return False, "Email has already been verified."
        
        verification.verify()
        return True, "Email verified successfully!"
        
    except EmailVerification.DoesNotExist:
        return False, "Invalid verification link."
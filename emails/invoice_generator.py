"""
PDF Invoice Generation for Tax Invoices
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
import logging

logger = logging.getLogger(__name__)

class InvoiceGenerator:
    """Generate PDF invoices for tax invoices"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom styles for invoice"""
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2C5F5F'),
            spaceAfter=5,
        ))
        
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#2C5F5F'),
            alignment=TA_CENTER,
            spaceBefore=10,
            spaceAfter=20,
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#2C5F5F'),
            spaceBefore=15,
            spaceAfter=8,
        ))
        
        self.styles.add(ParagraphStyle(
            name='InvoiceDetails',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceBefore=3,
            spaceAfter=3,
        ))
    
    def generate_invoice_pdf(self, tax_invoice) -> bytes:
        """Generate PDF invoice from TaxInvoice model"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                topMargin=0.8*inch,
                bottomMargin=0.8*inch,
                leftMargin=0.6*inch,
                rightMargin=0.6*inch
            )
            
            # Build the invoice content
            story = []
            
            # Company Header
            story.append(Paragraph("CodeLearn LMS", self.styles['CompanyName']))
            story.append(Paragraph("Learn. Code. Excel.", self.styles['Normal']))
            story.append(Paragraph("support@codelearn.com | www.codelearn.com", self.styles['Normal']))
            story.append(Spacer(1, 15))
            
            # Invoice Title
            story.append(Paragraph("TAX INVOICE", self.styles['InvoiceTitle']))
            story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2C5F5F')))
            story.append(Spacer(1, 20))
            
            # Invoice Details Table
            invoice_data = [
                ['Invoice Number:', tax_invoice.invoice_number],
                ['Invoice Date:', tax_invoice.created_at.strftime('%B %d, %Y')],
                ['Due Date:', tax_invoice.created_at.strftime('%B %d, %Y')],  # Immediate payment
                ['Status:', 'PAID' if tax_invoice.payment.status == 'completed' else 'PENDING'],
            ]
            
            invoice_table = Table(invoice_data, colWidths=[2*inch, 3*inch])
            invoice_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            story.append(invoice_table)
            story.append(Spacer(1, 20))
            
            # Billing Information
            story.append(Paragraph("Bill To:", self.styles['SectionHeader']))
            
            enrollment = tax_invoice.enrollment
            billing_info = f"""
            <b>{enrollment.user.name}</b><br/>
            {enrollment.user.email}<br/>
            {enrollment.user.phone_number or 'Phone: Not provided'}
            """
            story.append(Paragraph(billing_info, self.styles['InvoiceDetails']))
            story.append(Spacer(1, 20))
            
            # Course Details
            story.append(Paragraph("Course Details:", self.styles['SectionHeader']))
            
            course_data = [
                ['Description', 'Quantity', 'Unit Price', 'Amount'],
                [
                    f"{enrollment.course.title}\nOnline Course Access",
                    '1',
                    f"₹{tax_invoice.subtotal:,.2f}",
                    f"₹{tax_invoice.subtotal:,.2f}"
                ]
            ]
            
            course_table = Table(course_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
            course_table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C5F5F')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                
                # Data rows
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                
                # All cells
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            story.append(course_table)
            story.append(Spacer(1, 20))
            
            # Tax Calculation
            tax_data = [
                ['Subtotal:', f"₹{tax_invoice.subtotal:,.2f}"],
                [f'GST ({tax_invoice.tax_rate}%):', f"₹{tax_invoice.tax_amount:,.2f}"],
                ['', ''],  # Empty row for spacing
                ['Total Amount:', f"₹{tax_invoice.total_amount:,.2f}"],
            ]
            
            tax_table = Table(tax_data, colWidths=[4*inch, 2*inch])
            tax_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 2), 'Helvetica'),
                ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('FONTSIZE', (0, 3), (-1, 3), 14),
                
                # Total row styling
                ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#2C5F5F')),
                ('TEXTCOLOR', (0, 3), (-1, 3), colors.whitesmoke),
                ('LINEABOVE', (0, 3), (-1, 3), 2, colors.HexColor('#2C5F5F')),
                
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 3), (-1, 3), 10),
                ('BOTTOMPADDING', (0, 3), (-1, 3), 10),
            ]))
            
            story.append(tax_table)
            story.append(Spacer(1, 30))
            
            # Payment Information
            if tax_invoice.payment.payment_method == 'razorpay':
                story.append(Paragraph("Payment Information:", self.styles['SectionHeader']))
                payment_info = f"""
                Payment Method: Razorpay<br/>
                Transaction ID: {tax_invoice.payment.transaction_id}<br/>
                Payment Date: {tax_invoice.payment.payment_date.strftime('%B %d, %Y')}<br/>
                Status: <b>COMPLETED</b>
                """
                story.append(Paragraph(payment_info, self.styles['InvoiceDetails']))
                story.append(Spacer(1, 20))
            
            # Footer
            story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
            story.append(Spacer(1, 10))
            
            footer_text = """
            <b>Terms & Conditions:</b><br/>
            • This is a computer-generated invoice.<br/>
            • All payments are final and non-refundable as per our terms of service.<br/>
            • For any queries, please contact support@codelearn.com<br/>
            • GST Registration Number: [Your GST Number Here]
            """
            story.append(Paragraph(footer_text, self.styles['InvoiceDetails']))
            
            # Generate PDF
            doc.build(story)
            
            # Get PDF content
            pdf_content = buffer.getvalue()
            buffer.close()
            
            logger.info(f"Generated PDF invoice for Tax Invoice ID: {tax_invoice.id}")
            return pdf_content
            
        except Exception as e:
            logger.error(f"Error generating PDF invoice: {str(e)}")
            raise


def generate_invoice_pdf(tax_invoice) -> bytes:
    """Convenience function to generate invoice PDF"""
    generator = InvoiceGenerator()
    return generator.generate_invoice_pdf(tax_invoice)
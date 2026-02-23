from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class TermsView(View):
    """Terms and Conditions page."""
    template_name = 'pages/terms.html'
    
    def get(self, request):
        return render(request, self.template_name)


class PrivacyView(View):
    """Privacy Policy page."""
    template_name = 'pages/privacy.html'
    
    def get(self, request):
        return render(request, self.template_name)


class RefundView(View):
    """Refund Policy page."""
    template_name = 'pages/refund.html'
    
    def get(self, request):
        return render(request, self.template_name)


class HelpView(View):
    """Help Center page."""
    template_name = 'pages/help.html'
    
    def get(self, request):
        return render(request, self.template_name)


class ContactView(View):
    """Contact Us page - sends email instead of MongoDB."""
    template_name = 'pages/contact.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        name = request.POST.get('name', '').strip()[:100]
        email = request.POST.get('email', '').strip()[:100]
        subject = request.POST.get('subject', '').strip()[:200]
        message = request.POST.get('message', '').strip()[:2000]
        
        if name and email and message:
            try:
                # Send email notification
                send_mail(
                    subject=f'[Contact Form] {subject or "No Subject"}',
                    message=f'''
Name: {name}
Email: {email}
Subject: {subject}

Message:
{message}
''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    fail_silently=True,
                )
                
                messages.success(request, 'Your message has been sent successfully! We will get back to you soon.')
            except Exception as e:
                logger.error(f"Contact form error: {e}", exc_info=True)
                messages.error(request, 'There was an error sending your message. Please try again later.')
        else:
            messages.error(request, 'Please fill in all required fields.')
        
        return redirect('contact')


class AboutView(View):
    """About Us page."""
    template_name = 'pages/about.html'
    
    def get(self, request):
        return render(request, self.template_name)

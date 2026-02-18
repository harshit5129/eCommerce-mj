from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from datetime import datetime


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
    """Contact Us page."""
    template_name = 'pages/contact.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        subject = request.POST.get('subject', '')
        message = request.POST.get('message', '')
        
        if name and email and message:
            from mongoengine import Document, StringField, DateTimeField
            
            class ContactMessage(Document):
                name = StringField(required=True)
                email = StringField(required=True)
                subject = StringField()
                message = StringField(required=True)
                created_at = DateTimeField(default=datetime.utcnow)
                
                meta = {'collection': 'contact_messages'}
            
            ContactMessage(
                name=name,
                email=email,
                subject=subject,
                message=message
            ).save()
            
            messages.success(request, 'Your message has been sent successfully! We will get back to you soon.')
        else:
            messages.error(request, 'Please fill in all required fields.')
        
        return redirect('contact')


class AboutView(View):
    """About Us page."""
    template_name = 'pages/about.html'
    
    def get(self, request):
        return render(request, self.template_name)

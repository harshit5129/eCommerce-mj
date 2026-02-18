import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from decimal import Decimal
import json
import uuid
import logging

from orders.models import Order, PaymentTransaction

logger = logging.getLogger(__name__)


class RazorpayClient:
    """Razorpay client singleton."""
    
    _client = None
    
    @classmethod
    def get_client(cls):
        if cls._client is None:
            if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
                cls._client = razorpay.Client(
                    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
                )
        return cls._client
    
    @classmethod
    def is_configured(cls):
        return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


@method_decorator(csrf_exempt, name='dispatch')
class CreateRazorpayOrderView(View):
    """Create a Razorpay order for payment."""
    
    def post(self, request):
        if not RazorpayClient.is_configured():
            return JsonResponse({
                'error': 'Razorpay is not configured'
            }, status=400)
        
        try:
            data = json.loads(request.body.decode('utf-8'))
            order_number = data.get('order_number')
            
            if not order_number:
                return JsonResponse({'error': 'Order number is required'}, status=400)
            
            try:
                order = Order.objects.get(order_number=order_number)
            except Order.DoesNotExist:
                return JsonResponse({'error': 'Order not found'}, status=404)
            
            # Check if order is already paid
            if order.payment_status == 'paid':
                return JsonResponse({
                    'error': 'Order is already paid'
                }, status=400)
            
            client = RazorpayClient.get_client()
            
            # Create Razorpay order
            amount = int(order.total * 100)  # Convert to paise
            razorpay_order_data = {
                'amount': amount,
                'currency': 'INR',
                'receipt': order.order_number,
                'payment_capture': 1  # Auto capture
            }
            
            razorpay_order = client.order.create(data=razorpay_order_data)
            
            # Update order with Razorpay order ID
            order.razorpay_order_id = razorpay_order['id']
            order.save()
            
            # Create payment transaction
            transaction = PaymentTransaction.objects.create(
                order=order,
                transaction_id=str(uuid.uuid4()),
                payment_method='razorpay',
                amount=order.total,
                status='initiated',
                razorpay_order_id=razorpay_order['id'],
                response_data=razorpay_order
            )
            
            logger.info(f"Razorpay order created: {razorpay_order['id']} for order {order_number}")
            
            return JsonResponse({
                'success': True,
                'order_id': razorpay_order['id'],
                'amount': amount,
                'currency': 'INR',
                'key_id': settings.RAZORPAY_KEY_ID,
                'order_number': order.order_number,
                'prefill': {
                    'name': f"{order.shipping_address.get('first_name', '')} {order.shipping_address.get('last_name', '')}".strip(),
                    'email': order.user_email,
                    'contact': order.shipping_address.get('phone', '')
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error creating Razorpay order: {e}", exc_info=True)
            return JsonResponse({
                'error': 'Failed to create payment order'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class VerifyRazorpayPaymentView(View):
    """Verify Razorpay payment signature and update order."""
    
    def post(self, request):
        if not RazorpayClient.is_configured():
            return JsonResponse({
                'error': 'Razorpay is not configured'
            }, status=400)
        
        try:
            data = json.loads(request.body.decode('utf-8'))
            
            razorpay_order_id = data.get('razorpay_order_id')
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_signature = data.get('razorpay_signature')
            order_number = data.get('order_number')
            
            if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
                return JsonResponse({
                    'error': 'Missing payment details'
                }, status=400)
            
            # Verify signature
            client = RazorpayClient.get_client()
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            try:
                client.utility.verify_payment_signature(params_dict)
                signature_valid = True
            except razorpay.errors.SignatureVerificationError:
                signature_valid = False
            
            # Get order
            try:
                order = Order.objects.get(
                    order_number=order_number,
                    razorpay_order_id=razorpay_order_id
                )
            except Order.DoesNotExist:
                return JsonResponse({'error': 'Order not found'}, status=404)
            
            # Get payment details from Razorpay
            try:
                payment = client.payment.fetch(razorpay_payment_id)
                payment_status = payment.get('status')
                captured = payment.get('captured', False)
            except Exception as e:
                logger.error(f"Error fetching payment from Razorpay: {e}")
                payment_status = 'unknown'
                captured = False
            
            # Update payment transaction
            transaction = PaymentTransaction.objects.filter(
                order=order,
                razorpay_order_id=razorpay_order_id
            ).first()
            
            if signature_valid and payment_status == 'captured' and captured:
                # Payment successful
                order.payment_status = 'paid'
                order.razorpay_payment_id = razorpay_payment_id
                order.razorpay_signature = razorpay_signature
                order.save()
                
                if transaction:
                    transaction.razorpay_payment_id = razorpay_payment_id
                    transaction.razorpay_signature = razorpay_signature
                    transaction.status = 'success'
                    transaction.response_data = payment
                    transaction.save()
                
                # Send confirmation email
                from orders.views import send_order_confirmation_email
                send_order_confirmation_email(order)
                
                # Clear pending order from session
                if 'pending_order_number' in request.session:
                    del request.session['pending_order_number']
                
                # Clear cart and applied coupon
                request.session['cart'] = []
                if 'applied_coupon' in request.session:
                    del request.session['applied_coupon']
                request.session.modified = True
                
                logger.info(f"Payment verified successfully for order {order_number}")
                
                return JsonResponse({
                    'success': True,
                    'message': 'Payment successful',
                    'order_number': order.order_number,
                    'redirect_url': f'/orders/success/?order={order.order_number}'
                })
            else:
                # Payment failed
                order.payment_status = 'failed'
                order.save()
                
                if transaction:
                    transaction.razorpay_payment_id = razorpay_payment_id
                    transaction.status = 'failed'
                    transaction.error_message = f"Payment failed. Status: {payment_status}"
                    transaction.response_data = payment
                    transaction.save()
                
                logger.warning(f"Payment verification failed for order {order_number}")
                
                return JsonResponse({
                    'success': False,
                    'error': 'Payment verification failed',
                    'order_number': order.order_number
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error verifying Razorpay payment: {e}", exc_info=True)
            return JsonResponse({
                'error': 'Failed to verify payment'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(View):
    """Handle Razorpay webhooks for payment events."""
    
    def post(self, request):
        try:
            webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
            
            if not webhook_secret:
                logger.warning("Razorpay webhook secret not configured")
                return JsonResponse({'status': 'ignored'})
            
            webhook_body = request.body
            webhook_signature = request.headers.get('X-Razorpay-Signature')
            
            if not webhook_signature:
                return JsonResponse({'error': 'Missing signature'}, status=400)
            
            # Verify webhook signature
            client = RazorpayClient.get_client()
            
            try:
                client.utility.verify_webhook_signature(
                    webhook_body,
                    webhook_signature,
                    webhook_secret
                )
            except razorpay.errors.SignatureVerificationError:
                logger.warning("Invalid webhook signature")
                return JsonResponse({'error': 'Invalid signature'}, status=400)
            
            # Process webhook
            data = json.loads(webhook_body.decode('utf-8'))
            event = data.get('event')
            payload = data.get('payload', {})
            
            logger.info(f"Received Razorpay webhook: {event}")
            
            if event == 'payment.captured':
                payment_entity = payload.get('payment', {}).get('entity', {})
                razorpay_order_id = payment_entity.get('order_id')
                razorpay_payment_id = payment_entity.get('id')
                
                if razorpay_order_id:
                    try:
                        order = Order.objects.get(razorpay_order_id=razorpay_order_id)
                        
                        if order.payment_status != 'paid':
                            order.payment_status = 'paid'
                            order.razorpay_payment_id = razorpay_payment_id
                            order.save()
                            
                            logger.info(f"Order {order.order_number} marked as paid via webhook")
                    except Order.DoesNotExist:
                        logger.warning(f"Order not found for webhook: {razorpay_order_id}")
            
            elif event == 'payment.failed':
                payment_entity = payload.get('payment', {}).get('entity', {})
                razorpay_order_id = payment_entity.get('order_id')
                
                if razorpay_order_id:
                    try:
                        order = Order.objects.get(razorpay_order_id=razorpay_order_id)
                        order.payment_status = 'failed'
                        order.save()
                        
                        logger.info(f"Order {order.order_number} marked as failed via webhook")
                    except Order.DoesNotExist:
                        pass
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}", exc_info=True)
            return JsonResponse({'error': 'Webhook processing failed'}, status=500)


class PaymentStatusView(View):
    """Get payment status for an order."""
    
    def get(self, request):
        order_number = request.GET.get('order_number')
        
        if not order_number:
            return JsonResponse({'error': 'Order number required'}, status=400)
        
        try:
            order = Order.objects.get(order_number=order_number)
            
            # Check if user is authorized
            if request.user.is_authenticated:
                if order.user_id != str(request.user.id) and not request.user.is_staff:
                    return JsonResponse({'error': 'Not authorized'}, status=403)
            
            return JsonResponse({
                'order_number': order.order_number,
                'payment_status': order.payment_status,
                'payment_method': order.payment_method,
                'total': float(order.total),
                'is_paid': order.payment_status == 'paid'
            })
            
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)

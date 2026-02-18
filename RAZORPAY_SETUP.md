# Razorpay Payment Integration

This e-commerce application now supports **Razorpay** for online payments in addition to Cash on Delivery.

## Features

- ✅ Multiple payment methods (Card, UPI, NetBanking, Wallet)
- ✅ Secure payment signature verification
- ✅ Payment webhook support for async updates
- ✅ Payment transaction logging
- ✅ Automatic order confirmation after successful payment
- ✅ Inventory management with payment verification

## Configuration

### 1. Get Razorpay Keys

1. Sign up at [Razorpay Dashboard](https://dashboard.razorpay.com/)
2. Switch to **Test Mode** for development
3. Go to Settings → API Keys
4. Generate new keys (Key ID and Key Secret)

### 2. Update Environment Variables

Edit the `.env` file in your project root:

```env
# Razorpay Configuration
RAZORPAY_KEY_ID=rzp_test_XXXXXXXXXXXXXX
RAZORPAY_KEY_SECRET=your_secret_key_here
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret_here
```

### 3. Set Up Webhooks (Optional but Recommended)

For production, set up webhooks to handle payment events:

1. In Razorpay Dashboard → Settings → Webhooks
2. Add webhook URL: `https://yourdomain.com/orders/webhook/razorpay/`
3. Select events: `payment.captured`, `payment.failed`
4. Copy the webhook secret and add to `.env`

## Test Cards

Use these test card details for development:

### Successful Payment
- **Card Number**: 5267 3181 8797 5449
- **Expiry**: Any future date (e.g., 12/25)
- **CVV**: Any 3 digits (e.g., 123)
- **OTP**: 1234

### Failed Payment
- **Card Number**: 4111 1111 1111 1111
- **Result**: Payment will fail

## How It Works

1. **Customer selects "Pay Online"** at checkout
2. **Order is created** with pending payment status
3. **Razorpay order is created** via API
4. **Razorpay Checkout** opens with payment options
5. **Customer completes payment** in the modal
6. **Signature is verified** on the server
7. **Order is confirmed** and confirmation email sent
8. **Cart is cleared** after successful payment

## API Endpoints

- `POST /orders/payment/create/` - Create Razorpay order
- `POST /orders/payment/verify/` - Verify payment signature
- `GET /orders/payment/status/` - Get payment status
- `POST /orders/webhook/razorpay/` - Razorpay webhook handler

## Database Schema

### Order Model Updates
```python
razorpay_order_id    # Razorpay order ID
razorpay_payment_id  # Payment ID after successful transaction
razorpay_signature   # Signature for verification
payment_method       # 'cash', 'card', or 'razorpay'
payment_status       # 'pending', 'paid', 'failed', 'refunded'
```

### PaymentTransaction Model
Stores all payment attempts for audit trail:
```python
transaction_id       # Unique transaction ID
order               # Foreign key to Order
payment_method      # Payment method used
amount              # Transaction amount
status              # pending/initiated/success/failed/refunded
razorpay_order_id   # Razorpay order ID
razorpay_payment_id # Razorpay payment ID
error_code          # Error code if failed
error_message       # Error details
response_data       # Full API response (JSON)
```

## Troubleshooting

### Payment not working
1. Check if keys are configured in `.env`
2. Verify keys are from Test Mode (not Live)
3. Check Django logs for errors
4. Ensure migrations are applied: `python manage.py migrate`

### Webhook not receiving events
1. Verify webhook URL is publicly accessible
2. Check webhook secret is correct
3. Ensure HTTPS is used in production
4. Check server logs for webhook errors

### Order stuck in pending
1. Check PaymentTransaction records in admin
2. Verify Razorpay order was created
3. Check if payment was captured in Razorpay dashboard

## Production Checklist

- [ ] Switch to Live Mode keys
- [ ] Enable webhook secret
- [ ] Use HTTPS for all URLs
- [ ] Set up proper error monitoring
- [ ] Configure email notifications
- [ ] Test refund flow
- [ ] Set up payment reconciliation

## Support

For Razorpay support:
- Documentation: https://razorpay.com/docs/
- Test Mode Guide: https://razorpay.com/docs/payments/payments/test-card-details/
- API Reference: https://razorpay.com/docs/api/

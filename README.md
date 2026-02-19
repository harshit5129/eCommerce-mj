# 🛒 E-Commerce Django Application

A production-ready e-commerce web application built with Django, PostgreSQL, and Tailwind CSS featuring a modern dark crimson theme.

![Django](https://img.shields.io/badge/Django-4.2+-green.svg)
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

### 🛍️ Storefront
- **Product Catalog**: Browse products with search, filters, and sorting
- **Product Details**: Image gallery, reviews, related products
- **Shopping Cart**: Add/remove items, quantity management
- **Wishlist**: Save favorite products
- **User Reviews**: Ratings, photos, videos with helpful voting

### 🔐 Authentication
- User registration with email verification
- JWT-based API authentication
- Session-based web authentication
- Password reset with secure tokens
- Social login ready

### 💳 Payments
- Razorpay payment integration
- Multiple payment methods
- Webhook handling for payment status
- Order confirmation emails

### 📊 Admin Panel
- Custom admin dashboard with analytics
- Product management with multiple images
- Order management with status updates
- Coupon and offer management
- Review moderation
- User management

### 🎨 Frontend
- Modern dark crimson/orange theme
- Responsive design with Tailwind CSS
- Image carousels and sliders
- AJAX-powered cart and wishlist
- Real-time notifications

## 🚀 Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Django 4.2+ |
| **Database** | PostgreSQL 14+ |
| **Cache/Session** | Redis |
| **Task Queue** | Celery |
| **Frontend** | Tailwind CSS, JavaScript |
| **API** | Django REST Framework |
| **Authentication** | JWT (SimpleJWT) |
| **Payments** | Razorpay |
| **Static Files** | WhiteNoise |

## 📋 Requirements

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Node.js 18+ (for Tailwind CLI, optional)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/ecomm.git
cd ecomm
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Required
SECRET_KEY=your-secure-50-character-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=ecomm_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/1

# Razorpay
RAZORPAY_KEY_ID=your-key-id
RAZORPAY_KEY_SECRET=your-key-secret
```

### 5. Setup Database

```bash
# Create PostgreSQL database
sudo -u postgres createdb ecomm_db

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 6. Run Development Server

```bash
python manage.py runserver
```

Visit http://localhost:8000

## 🐳 Docker Setup

```bash
# Build and run
docker-compose up --build

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

## 📁 Project Structure

```
ecomm/
├── config/                 # Django configuration
│   ├── settings/          # Environment-specific settings
│   │   ├── base.py       # Common settings
│   │   ├── development.py # Development settings
│   │   └── production.py # Production settings
│   ├── urls.py            # Main URL configuration
│   ├── celery.py          # Celery configuration
│   └── wsgi.py            # WSGI configuration
│
├── users/                  # User management
│   ├── models.py          # User, Address, CartItem models
│   ├── views.py           # Auth views
│   └── api_views.py       # User API endpoints
│
├── products/               # Product catalog
│   ├── models.py          # Product, Category, ProductImage
│   ├── views.py           # Product views
│   └── api_views.py       # Product API endpoints
│
├── orders/                 # Order management
│   ├── models.py          # Order, OrderItem, PaymentTransaction
│   ├── views.py           # Order views
│   └── razorpay_views.py  # Payment integration
│
├── offers/                 # Offers and discounts
│   ├── models.py          # Coupon, LimitedOffer, ProductReview
│   └── views.py           # Offer views
│
├── cart/                   # Shopping cart
│   ├── views.py           # Cart views
│   └── api_views.py       # Cart API endpoints
│
├── analytics/              # Analytics tracking
├── core/                   # Core utilities
├── cookies/                # Cookie consent
├── pages/                  # Static pages
│
├── templates/              # HTML templates
│   ├── base.html          # Main base template
│   ├── admin/             # Admin templates
│   ├── products/          # Product templates
│   ├── orders/            # Order templates
│   ├── users/             # User templates
│   └── partials/          # Reusable components
│
├── static/                 # Static files
│   └── js/                # JavaScript files
│
├── media/                  # User uploads
│
├── requirements.txt        # Python dependencies
├── gunicorn.conf.py       # Gunicorn configuration
└── docker-compose.yml     # Docker configuration
```

## 🔌 API Endpoints

### Products
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products/` | List products with filters |
| GET | `/api/products/<id>/` | Product details |
| GET | `/api/products/featured/` | Featured products |

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login user |
| POST | `/api/auth/logout/` | Logout user |
| GET | `/api/auth/profile/` | User profile |

### Cart
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cart/` | Get cart |
| POST | `/api/cart/add/` | Add item to cart |
| POST | `/api/cart/update/` | Update item quantity |
| POST | `/api/cart/remove/` | Remove item |
| POST | `/api/cart/clear/` | Clear cart |

### Orders
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orders/` | List user orders |
| POST | `/api/orders/create/` | Create order |
| GET | `/api/orders/<number>/` | Order details |
| POST | `/api/orders/cancel/` | Cancel order |

### Offers
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/offers/coupon/apply/` | Apply coupon |
| POST | `/api/offers/coupon/remove/` | Remove coupon |
| GET | `/api/offers/offers/active/` | Active offers |

## 🔒 Security Features

- ✅ CSRF protection
- ✅ XSS prevention (auto-escaping)
- ✅ SQL injection prevention (ORM)
- ✅ Rate limiting
- ✅ Secure session cookies
- ✅ JWT token authentication
- ✅ Payment signature verification
- ✅ Input validation
- ✅ Audit logging

## 📊 Performance Optimizations

- Database indexes on key fields
- Redis caching
- Query optimization with `select_related`/`prefetch_related`
- Static file compression (WhiteNoise)
- Lazy loading images

## 🧪 Running Tests

```bash
# Run all tests
python manage.py test

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

## 🚀 Deployment

### Production Checklist

1. Set environment variables:
   ```env
   DEBUG=False
   SECRET_KEY=your-production-secret-key
   SECURE_SSL_REDIRECT=True
   SECURE_HSTS=True
   CSRF_COOKIE_SECURE=True
   SESSION_COOKIE_SECURE=True
   ```

2. Collect static files:
   ```bash
   python manage.py collectstatic --noinput
   ```

3. Run with Gunicorn:
   ```bash
   gunicorn config.wsgi:application
   ```

### Deploy to Render/Heroku

1. Push code to GitHub
2. Connect repository to platform
3. Set environment variables
4. Deploy

### Deploy to VPS

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static
python manage.py collectstatic

# Start Gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

## 📝 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Django secret key | ✅ |
| `DEBUG` | Debug mode | ✅ |
| `ALLOWED_HOSTS` | Allowed hosts | ✅ |
| `DB_NAME` | Database name | ✅ |
| `DB_USER` | Database user | ✅ |
| `DB_PASSWORD` | Database password | ✅ |
| `DB_HOST` | Database host | ✅ |
| `REDIS_URL` | Redis connection URL | ✅ |
| `RAZORPAY_KEY_ID` | Razorpay key ID | ✅ |
| `RAZORPAY_KEY_SECRET` | Razorpay secret | ✅ |
| `JWT_SECRET_KEY` | JWT secret key | ✅ |
| `EMAIL_HOST_USER` | Email user | ❌ |
| `EMAIL_HOST_PASSWORD` | Email password | ❌ |

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## 📧 Support

- Create an issue for bugs
- Email: support@eshop.com

---

Built with ❤️ using Django

# E-Commerce Django Application

A production-ready e-commerce web application built with Django, MongoDB, Vanilla JavaScript, and Tailwind CSS.

## Features

### Core Features
- User registration, login, and logout
- JWT-based authentication
- Product listing with search and filtering
- Product detail pages
- Shopping cart functionality
- Checkout process
- Order creation and history
- User profile management

### API Features (Phase 2)
- RESTful API with Django REST Framework
- JWT authentication
- Product API with pagination and filtering
- Cart API
- Order API

## Tech Stack

- **Backend**: Django 4.2+
- **Database**: MongoDB with MongoEngine
- **Frontend**: HTML5, Tailwind CSS, Vanilla JavaScript
- **API**: Django REST Framework
- **Authentication**: JWT (djangorestframework-simplejwt)

## Why MongoEngine over Djongo?

We chose MongoEngine for the following reasons:

1. **Stability**: MongoEngine is more mature and stable than Djongo
2. **Documentation**: Better documentation and community support
3. **Maintenance**: Actively maintained and updated
4. **Flexibility**: More flexible for MongoDB-specific features
5. **Compatibility**: Fewer compatibility issues with Django versions

## Database Design

### Embedding vs Referencing

- **Cart Items**: Embedded in User document (small, frequently accessed)
- **Order Items**: Embedded in Order document (complete snapshot)
- **Product in Cart**: Reference (product can change independently)
- **User in Orders**: Reference (user can have many orders)

### Index Strategy

- Products: `slug`, `sku`, `price`, `is_active`, text index for search
- Users: `email`, `username`
- Orders: `user_id`, `order_number`, `created_at`

## Getting Started

### Prerequisites

- Python 3.11+
- MongoDB 6.0+
- pip

### Installation

1. Clone the repository
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy environment file:
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` with your settings:
   ```
   SECRET_KEY=your-secret-key
   MONGODB_HOST=localhost
   MONGODB_PORT=27017
   MONGODB_NAME=ecomm_db
   ```

6. Run migrations (MongoDB doesn't require traditional migrations):
   ```bash
   python manage.py
   ```

7. Create sample data:
   ```bash
   python manage.py create_sample_data
   ```

8. Run development server:
   ```bash
   python manage.py runserver
   ```

### Docker Setup

```bash
docker-compose up --build
```

## Project Structure

```
ecomm/
├── config/              # Django configuration
│   ├── settings/       # Settings (base, dev, prod)
│   ├── urls.py         # Main URL configuration
│   └── wsgi.py         # WSGI configuration
├── users/              # User authentication app
│   ├── models.py       # User model
│   ├── views.py        # Authentication views
│   └── urls.py         # URL routing
├── products/           # Products app
│   ├── models.py       # Product model
│   ├── views.py        # Product views
│   └── urls.py         # URL routing
├── cart/               # Shopping cart app
│   ├── models.py      # Cart models
│   ├── views.py       # Cart views
│   └── urls.py        # URL routing
├── orders/             # Orders app
│   ├── models.py      # Order model
│   ├── views.py       # Order views
│   └── urls.py        # URL routing
├── templates/          # HTML templates
├── static/            # Static files
│   ├── css/          # CSS files
│   └── js/           # JavaScript files
└── manage.py         # Django management script
```

## Deployment

### Docker

```bash
docker build -t ecomm .
docker run -p 8000:8000 ecomm
```

### Render

1. Connect your GitHub repository to Render
2. Set environment variables
3. Add MongoDB addon (MongoDB Atlas)
4. Deploy

### VPS (Ubuntu)

```bash
# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic

# Run with Gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| SECRET_KEY | Django secret key | Required |
| DEBUG | Debug mode | False |
| MONGODB_HOST | MongoDB host | localhost |
| MONGODB_PORT | MongoDB port | 27017 |
| MONGODB_NAME | Database name | ecomm_db |
| JWT_SECRET_KEY | JWT secret key | Required |
| ALLOWED_HOSTS | Allowed hosts | localhost |

## API Endpoints

### Products
- `GET /api/products/` - List products
- `GET /api/products/<id>/` - Get product detail
- `GET /api/products/featured/` - Featured products

### Users
- `POST /api/auth/register/` - Register user
- `POST /api/auth/login/` - Login user
- `GET /api/auth/profile/` - Get user profile

### Cart
- `GET /api/cart/` - Get cart
- `POST /api/cart/add/` - Add to cart
- `POST /api/cart/update/` - Update cart item
- `POST /api/cart/remove/` - Remove from cart

### Orders
- `GET /api/orders/` - List orders
- `POST /api/orders/create/` - Create order

## License

MIT License

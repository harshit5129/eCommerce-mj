from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views import View
from products.models import Product
import math


class HomeView(View):
    """Home page with featured products."""
    
    template_name = 'products/home.html'
    
    def get(self, request):
        featured_products = Product.objects(is_featured=True, is_active=True)[:8]
        latest_products = Product.objects(is_active=True).order_by('-created_at')[:12]
        
        context = {
            'featured_products': featured_products,
            'latest_products': latest_products,
        }
        return render(request, self.template_name, context)


class ProductListView(View):
    """Product listing page with filtering and search."""
    
    template_name = 'products/product_list.html'
    
    def get(self, request):
        page = int(request.GET.get('page', 1))
        per_page = 12
        category = request.GET.get('category')
        search = request.GET.get('search')
        sort = request.GET.get('sort', '-created_at')
        
        products = Product.objects(is_active=True)
        
        if category:
            products = products(category__slug=category)
        
        if search:
            products = products.search(search)
        
        try:
            products = products.order_by(sort)
        except:
            products = products.order_by('-created_at')
        
        total_products = products.count()
        total_pages = math.ceil(total_products / per_page)
        
        start = (page - 1) * per_page
        end = start + per_page
        products = products[start:end]
        
        context = {
            'products': products,
            'page': page,
            'total_pages': total_pages,
            'total_products': total_products,
            'category': category,
            'search': search,
            'sort': sort,
        }
        return render(request, self.template_name, context)


class ProductDetailView(View):
    """Product detail page."""
    
    template_name = 'products/product_detail.html'
    
    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug, is_active=True)
        
        related_products = Product.objects(
            category=product.category,
            is_active=True,
            id__ne=product.id
        )[:4]
        
        context = {
            'product': product,
            'related_products': related_products,
        }
        return render(request, self.template_name, context)

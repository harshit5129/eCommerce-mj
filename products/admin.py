from django.contrib import admin
from products.models import Category, Product, ProductImage, Wishlist


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'price', 'stock_quantity', 'is_active', 'is_featured', 'created_at']
    list_filter = ['is_active', 'is_featured', 'category', 'track_inventory']
    search_fields = ['name', 'sku', 'description']
    list_editable = ['price', 'is_active', 'is_featured']
    inlines = [ProductImageInline]
    date_hierarchy = 'created_at'


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'user_email', 'created_at']
    search_fields = ['user_email', 'user_id']
    filter_horizontal = ['products']

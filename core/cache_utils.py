from django.core.cache import cache
from functools import wraps
import hashlib
import json


def cache_result(timeout=300, key_prefix=''):
    """
    Decorator to cache function results.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = _generate_cache_key(func.__name__, args, kwargs, key_prefix)
            
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            result = func(*args, **kwargs)
            
            if result is not None:
                cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


def cache_model_method(timeout=300):
    """
    Decorator for model methods that should be cached.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            cache_key = f"model:{self.__class__.__name__}:{str(self.id)}:{func.__name__}"
            
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            result = func(self, *args, **kwargs)
            
            if result is not None:
                cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


def invalidate_cache(pattern):
    """
    Invalidate cache keys matching a pattern.
    """
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection('default')
        keys = conn.keys(f"*{pattern}*")
        if keys:
            conn.delete(*keys)
    except Exception:
        pass


def _generate_cache_key(func_name, args, kwargs, prefix):
    """
    Generate a unique cache key based on function name and arguments.
    """
    key_data = {
        'func': func_name,
        'args': [str(a) for a in args],
        'kwargs': {k: str(v) for k, v in sorted(kwargs.items())}
    }
    key_hash = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    return f"{prefix}:{func_name}:{key_hash}"


class ProductCache:
    """
    Product-specific caching utilities.
    """
    
    @staticmethod
    def get_product(product_id):
        key = f"product:{product_id}"
        return cache.get(key)
    
    @staticmethod
    def set_product(product_id, product_data, timeout=300):
        key = f"product:{product_id}"
        cache.set(key, product_data, timeout)
    
    @staticmethod
    def get_featured_products():
        return cache.get("products:featured")
    
    @staticmethod
    def set_featured_products(products, timeout=300):
        cache.set("products:featured", products, timeout)
    
    @staticmethod
    def invalidate_product(product_id):
        cache.delete(f"product:{product_id}")
        cache.delete("products:featured")
        cache.delete("products:latest")
    
    @staticmethod
    def get_categories():
        return cache.get("categories:all")
    
    @staticmethod
    def set_categories(categories, timeout=3600):
        cache.set("categories:all", categories, timeout)


class CartCache:
    """
    Cart-specific caching utilities.
    """
    
    @staticmethod
    def get_cart(user_id):
        key = f"cart:user:{user_id}"
        return cache.get(key)
    
    @staticmethod
    def set_cart(user_id, cart_data, timeout=86400):
        key = f"cart:user:{user_id}"
        cache.set(key, cart_data, timeout)
    
    @staticmethod
    def invalidate_cart(user_id):
        cache.delete(f"cart:user:{user_id}")

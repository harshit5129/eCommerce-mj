/**
 * E-Shop Cart JavaScript
 * Handles all cart operations with AJAX
 */

const Cart = {
    cartCount: 0,
    
    init: function() {
        this.updateCartCount();
    },
    
    /**
     * Add product to cart
     */
    addToCart: function(productId, quantity = 1) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: '/cart/add/',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    product_id: productId,
                    quantity: parseInt(quantity)
                }),
                success: (response) => {
                    if (response.success) {
                        this.updateCartBadge(response.cart_count);
                        this.showNotification(response.message, 'success');
                    }
                    resolve(response);
                },
                error: (xhr) => {
                    let error = 'An error occurred';
                    try {
                        const response = JSON.parse(xhr.responseText);
                        error = response.error || error;
                    } catch (e) {}
                    this.showNotification(error, 'error');
                    reject(error);
                }
            });
        });
    },
    
    /**
     * Update cart item quantity
     */
    updateQuantity: function(productId, quantity) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: '/cart/update/',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    product_id: productId,
                    quantity: parseInt(quantity)
                }),
                success: (response) => {
                    if (response.success) {
                        this.updateCartBadge(response.cart_count);
                        location.reload();
                    }
                    resolve(response);
                },
                error: (xhr) => {
                    let error = 'An error occurred';
                    try {
                        const response = JSON.parse(xhr.responseText);
                        error = response.error || error;
                    } catch (e) {}
                    this.showNotification(error, 'error');
                    reject(error);
                }
            });
        });
    },
    
    /**
     * Remove item from cart
     */
    removeFromCart: function(productId) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: '/cart/remove/',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    product_id: productId
                }),
                success: (response) => {
                    if (response.success) {
                        this.updateCartBadge(response.cart_count);
                        location.reload();
                    }
                    resolve(response);
                },
                error: (xhr) => {
                    let error = 'An error occurred';
                    try {
                        const response = JSON.parse(xhr.responseText);
                        error = response.error || error;
                    } catch (e) {}
                    this.showNotification(error, 'error');
                    reject(error);
                }
            });
        });
    },
    
    /**
     * Clear all cart items
     */
    clearCart: function() {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: '/cart/clear/',
                method: 'POST',
                contentType: 'application/json',
                success: (response) => {
                    if (response.success) {
                        this.updateCartBadge(0);
                        location.reload();
                    }
                    resolve(response);
                },
                error: (xhr) => {
                    let error = 'An error occurred';
                    try {
                        const response = JSON.parse(xhr.responseText);
                        error = response.error || error;
                    } catch (e) {}
                    this.showNotification(error, 'error');
                    reject(error);
                }
            });
        });
    },
    
    /**
     * Update cart badge count
     */
    updateCartBadge: function(count) {
        this.cartCount = count;
        const badge = $('#cart-count-badge');
        if (count > 0) {
            badge.text(count).removeClass('hidden');
        } else {
            badge.addClass('hidden');
        }
    },
    
    /**
     * Get current cart count from session
     */
    updateCartCount: function() {
        $.get('/cart/', (data) => {
            this.updateCartBadge(data.cart_count || 0);
        }).fail(() => {});
    },
    
    /**
     * Show notification toast
     */
    showNotification: function(message, type = 'info') {
        let bgColor = 'bg-blue-500';
        if (type === 'success') bgColor = 'bg-green-500';
        if (type === 'error') bgColor = 'bg-red-500';
        
        const toast = $(
            '<div class="fixed top-24 right-4 ' + bgColor + ' text-white px-6 py-3 rounded-lg shadow-lg z-50 transform transition-all duration-300 translate-x-full">' +
                message +
            '</div>'
        );
        
        $('body').append(toast);
        
        setTimeout(() => {
            toast.removeClass('translate-x-full');
        }, 100);
        
        setTimeout(() => {
            toast.addClass('translate-x-full');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
};

/**
 * Global function for adding to cart (used in templates)
 */
function addToCart(productId, quantity = 1) {
    Cart.addToCart(productId, quantity);
}

/**
 * Global function for updating quantity
 */
function updateQuantity(productId, quantity) {
    if (quantity < 1) {
        removeFromCart(productId);
        return;
    }
    Cart.updateQuantity(productId, quantity);
}

/**
 * Global function for removing from cart
 */
function removeFromCart(productId) {
    Cart.removeFromCart(productId);
}

/**
 * Global function for clearing cart
 */
function clearCart() {
    if (confirm('Are you sure you want to clear your cart?')) {
        Cart.clearCart();
    }
}

/**
 * Cancel order
 */
function cancelOrder(orderNumber) {
    if (!confirm('Are you sure you want to cancel this order?')) return;
    
    $.ajax({
        url: '/orders/cancel/',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ order_number: orderNumber }),
        success: (response) => {
            if (response.success) {
                Cart.showNotification(response.message, 'success');
                location.reload();
            }
        },
        error: (xhr) => {
            let error = 'An error occurred';
            try {
                const response = JSON.parse(xhr.responseText);
                error = response.error || error;
            } catch (e) {}
            Cart.showNotification(error, 'error');
        }
    });
}

/**
 * Initialize cart on document ready
 */
$(document).ready(function() {
    Cart.init();
});

/**
 * CSRF token helper
 */
function getCSRFToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Setup AJAX CSRF headers
 */
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!(/^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type))) {
            xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
        }
    }
});

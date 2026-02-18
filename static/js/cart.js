/**
 * E-Shop Cart JavaScript
 * Handles all cart operations with AJAX
 */

const Cart = {
    cartCount: 0,
    
    init: function() {
        this.updateCartCount();
    },
    
    addToCart: function(productId, quantity = 1) {
        return new Promise((resolve, reject) => {
            const btn = document.querySelector(`[onclick*="addToCart('${productId}'"]`);
            if (btn) {
                btn.innerHTML = '<svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';
                btn.disabled = true;
            }
            
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
                        if (btn) {
                            btn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg> Added!';
                            setTimeout(() => {
                                btn.innerHTML = '<span class="flex items-center justify-center gap-2"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"/></svg>Add to Cart</span>';
                                btn.disabled = false;
                            }, 1500);
                        }
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
                    if (btn) {
                        btn.innerHTML = '<span class="flex items-center justify-center gap-2"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"/></svg>Add to Cart</span>';
                        btn.disabled = false;
                    }
                    reject(error);
                }
            });
        });
    },
    
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
    
    updateCartBadge: function(count) {
        this.cartCount = count;
        const badge = $('#cart-count-badge');
        if (count > 0) {
            badge.text(count).removeClass('hidden').addClass('animate-bounce-in');
        } else {
            badge.addClass('hidden');
        }
    },
    
    updateCartCount: function() {
        $.get('/cart/', (data) => {
            this.updateCartBadge(data.cart_count || 0);
        }).fail(() => {});
    },
    
    showNotification: function(message, type = 'info') {
        const colors = {
            success: { bg: 'bg-green-500', icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>' },
            error: { bg: 'bg-red-500', icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>' },
            warning: { bg: 'bg-yellow-500', icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>' },
            info: { bg: 'bg-blue-500', icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>' }
        };
        
        const config = colors[type] || colors.info;
        
        const toast = $(
            '<div class="fixed top-24 right-4 ' + config.bg + ' text-white px-6 py-4 rounded-xl shadow-2xl z-50 transform transition-all duration-300 translate-x-full flex items-center gap-3 max-w-sm">' +
                '<svg class="w-6 h-6 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">' + config.icon + '</svg>' +
                '<span class="font-medium">' + message + '</span>' +
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

const Wishlist = {
    items: [],
    
    init: function() {
        this.items = JSON.parse(localStorage.getItem('wishlist') || '[]');
        this.updateBadges();
    },
    
    toggle: function(productId, productName, productImage, productPrice, productSlug) {
        const index = this.items.findIndex(item => item.id === productId);
        
        if (index > -1) {
            this.items.splice(index, 1);
            Cart.showNotification('Removed from wishlist', 'info');
        } else {
            this.items.push({
                id: productId,
                name: productName,
                image: productImage,
                price: productPrice,
                slug: productSlug
            });
            Cart.showNotification('Added to wishlist', 'success');
        }
        
        localStorage.setItem('wishlist', JSON.stringify(this.items));
        this.updateBadges();
    },
    
    isInWishlist: function(productId) {
        return this.items.some(item => item.id === productId);
    },
    
    updateBadges: function() {
        const count = this.items.length;
        $('.wishlist-count').text(count);
        if (count > 0) {
            $('.wishlist-count').removeClass('hidden');
        } else {
            $('.wishlist-count').addClass('hidden');
        }
    },
    
    getItems: function() {
        return this.items;
    },
    
    clear: function() {
        this.items = [];
        localStorage.removeItem('wishlist');
        this.updateBadges();
    }
};

function addToCart(productId, quantity = 1) {
    Cart.addToCart(productId, quantity);
}

function updateQuantity(productId, quantity) {
    if (quantity < 1) {
        removeFromCart(productId);
        return;
    }
    Cart.updateQuantity(productId, quantity);
}

function removeFromCart(productId) {
    Cart.removeFromCart(productId);
}

function clearCart() {
    if (confirm('Are you sure you want to clear your cart?')) {
        Cart.clearCart();
    }
}

function toggleWishlist(productId) {
    $.ajax({
        url: '/wishlist/toggle/' + productId + '/',
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken()
        },
        success: function(response) {
            if (response.success) {
                Cart.showNotification(response.message, response.action === 'added' ? 'success' : 'info');
                // Update wishlist count in header
                const badge = $('.wishlist-count');
                if (badge.length) {
                    badge.text(response.count);
                    if (response.count > 0) {
                        badge.removeClass('hidden');
                    } else {
                        badge.addClass('hidden');
                    }
                }
            }
        },
        error: function(xhr) {
            let error = 'An error occurred';
            try {
                const response = JSON.parse(xhr.responseText);
                error = response.error || error;
            } catch (e) {}
            Cart.showNotification(error, 'error');
        }
    });
}

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

$(document).ready(function() {
    Cart.init();
    Wishlist.init();
});

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

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!(/^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type))) {
            xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
        }
    }
});

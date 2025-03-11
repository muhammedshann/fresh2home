from django.urls import path , include
from django.contrib.auth import views as auth_views
from . import views
from django.urls import path

# app_name = 'user'

urlpatterns = [
    # Home & Authentication
    path('', views.homepage, name='homepage'),
    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('forget_pass/', views.forgot_password, name='forgot_password'),

    # OTP Verification
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('send-otp/', views.send_otp_email, name='send_otp'),

    # Profile & User Management
    path('profile/', views.profile_view, name='profile'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('change_password/', views.change_password, name='change_password'),

    # Address Management
    path('profile/address/create/', views.address_create, name='address_create'),
    path('edit-address/<int:address_id>/', views.edit_address, name='edit_address'),
    path('delete-address/<int:address_id>/', views.delete_address, name='delete_address'),

    # Product & Category
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('category/<str:category_name>/', views.category_products, name='category_products'),
    path("search/", views.search, name="search"),

    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist_view'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),

    # Cart
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('cart/update_quantity/', views.update_cart_quantity, name='update_cart_quantity'),  # AJAX route
    path('cart/checkout/', views.checkout, name='checkout'),

    # Orders & Transactions
    path('order/<int:order_id>/', views.order_details, name='order_details'),
    path('order/cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('invoice/<int:order_id>/', views.download_invoice, name='download_invoice'),

    # Payment & Coupons
    path('apply_coupon/', views.apply_coupon, name='apply_coupon'),
    path('razorpay/callback/', views.razorpay_callback, name='razorpay_callback'),
    path('payment/', views.order_success, name='order_success'),
    path('add-money/', views.add_money, name='add_money'),
    path('payment-callback/', views.payment_callback, name='payment_callback'),
    path('orders/initiate_repayment_ajax/<int:order_id>/', views.initiate_repayment_ajax, name='initiate_repayment_ajax'),
    path('orders/ajax_razorpay_callback/', views.ajax_razorpay_callback, name='ajax_razorpay_callback'),

    # Referral System
    path('ref/<str:referral_id>/', views.referral_signup, name='referral_signup'),

    # Miscellaneous
    path('get-variant-info/', views.get_variant_info, name='get_variant_info'),
    path('password/', views.password, name='password'),

    # chatbot
    path("chatbot/", views.chatbot, name="chatbot"),
]
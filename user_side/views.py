from django.shortcuts import render, redirect ,get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.hashers import make_password
from user_side.models import User , Products,Category,Banner,ProductImage,Cart,CartItem,Address,CouponUsage,Wallet,Transaction,Order,Coupon,OrderItem,Payment,ProductVariant,Store,WalletTransaction,Wishlist,WishlistItem,Complaint
from django.contrib.auth.decorators import login_required
from .models import OTPVerification
from django.contrib.auth import update_session_auth_hash
from datetime import datetime ,timedelta
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from django.views.decorators.http import require_GET
import random ,string
from django.views.decorators.cache import never_cache
import random
from django.core.mail import send_mail
from django.http import HttpResponse,HttpResponseRedirect,JsonResponse
from django.db import transaction
import re,json
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.db.models import ProtectedError
from django.contrib.auth import logout
import razorpay,uuid
from reportlab.pdfgen import canvas
from xhtml2pdf import pisa
from django.template.loader import get_template


def send_otp_email(request):
    otp = generate_otp()

    # Email details
    subject = 'Your OTP Code'
    message = f'Your OTP code is {otp}. This code is valid for a short time.'
    recipient_list = ['fresh2homee@example.com'] 

    send_mail(subject, message, 'fresh2homee@gmail.com', recipient_list)

    return HttpResponse(f'OTP {otp} sent successfully to {recipient_list[0]}')

def generate_referral_id(username):
    return username[:3].upper() + uuid.uuid4().hex[:6].upper()

def referral_signup(request, referral_id):
    # Get the referrer user
    referrer = get_object_or_404(User, referral_id=referral_id)
    
    # Store the referrer's ID in the session
    request.session['referrer_id'] = referrer.referral_id
    # Redirect to the signup page
    return redirect('signup')

@never_cache
def login(request):
    if request.user.is_authenticated:
        messages.info(request, 'You are already logged in.')
        return redirect('homepage')
    elif request.user.is_superuser:
        messages.warning(request, 'This is now available for admin')
        return redirect('adminlogin')

    if request.method == 'POST':
        entry = request.POST['entry']
        password = request.POST['password']
        
        if '@' in entry:
            user = User.objects.filter(email=entry).first()
        else:
            user = User.objects.filter(username=entry).first()

        if user:
            if not user.is_active:
                messages.error(request, 'Your account is inactive.')
                return redirect('login')
            if not user.is_verify:
                messages.error(request, 'Please verify your email.')
                return redirect('login')
            
            user = authenticate(request, username=user.username, password=password)

            if user is not None:
                auth_login(request, user)  # Use the renamed import here
                messages.success(request, 'You have successfully logged in!')
                return redirect('homepage')
        
        messages.error(request, 'Invalid username or password.')
        return render(request, 'login.html')

    return render(request, 'login.html')


@never_cache
def signup(request):
    if request.user.is_authenticated:
        return redirect('homepage')

    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        phone_no = request.POST['phone']
        password = request.POST['password']
        # referral_id = generate_referral_id(username)

        # referred
        referrer_id = request.session.get('referrer_id')
        if referrer_id:
            referrer = User.objects.get(referral_id=referrer_id)
            del request.session['referrer_id']
        else:
            referrer = None

        # Validate
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('signup')
        
        if not re.match(r'^[a-zA-Z0-9_ ]{4,20}$', username):
            messages.error(request, 'Username must be 4-20 characters long and contain only letters, numbers, and underscores.')
            return redirect('signup')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists!')
            return redirect('signup')
            
        if User.objects.filter(phone_no=phone_no).exists():
            messages.error(request, 'Phone number already exists!')
            return redirect('signup')
        if not re.match(r'^\+?1?\d{9,15}$', phone_no):
            messages.error(request, 'Invalid phone number.')
            return redirect('signup')
        if not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password):
            messages.error(request, 'Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character.')
            return redirect('signup')


        # Generate OTP
        otp = generate_otp()
        print(otp)
        otp_expiry_time = timezone.now() + timedelta(minutes=5)
        # Send OTP email
        send_mail(
            'Your OTP for Email Verification',
            f'Your OTP is {otp}. It will expire in 5 minutes.',
            'fresh2home@example.com',  # Replace with your email
            [email],
            fail_silently=False,
        )

        # Create the user
        user = User.objects.create(
            username=username,
            email=email,
            phone_no=phone_no,
            password=make_password(password),
            referred_by=referrer  # referrer
        )
        Wallet.objects.create(user=user, balance=0)
        
        OTPVerification.objects.create(
            user=user,
            otp=otp,
            email_or_phone=email,
            expires_at=otp_expiry_time
        )
        request.session['next_page'] = 'login' 

        messages.success(request, 'Account created successfully! Please check your email for the OTP.')
        return redirect('verify_otp')

    return render(request, 'signup.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@never_cache
def homepage(request):
    if request.user.is_superuser:
        return redirect('adminlogin')
    
    products = Products.objects.filter(discount__gt=0).prefetch_related('images')
    category = Category.objects.all()
    banners = Banner.objects.all()
    context = {
        'products': products,
        'category': category,
        'banners': banners
    }

    return render(request, 'home_page.html', context)

def search(request):
    query = request.GET.get("q", "")
    selected_sort = request.GET.get("sort", "")

    result = Products.objects.filter(name__icontains=query) if query else Products.objects.none()

    # Sorting logic
    if selected_sort == "price_low":
        result = result.order_by("price")
    elif selected_sort == "price_high":
        result = result.order_by("-price")
    elif selected_sort == "name_asc":
        result = result.order_by("name")
    elif selected_sort == "newest":
        result = result.order_by("-created_at")

    return render(request, "category_products.html", {
        "products": result,
        "query": query,
        "selected_sort": selected_sort
    })


@require_GET
def get_variant_info(request):
    variant_id = request.GET.get('variant_id')
    try:
        variant = ProductVariant.objects.get(id=variant_id)
        data = {
            'original_price': float(variant.price),  # Show the original price
            'discounted_price': float(variant.discounted_price()),  # Show the discounted price
            'available_quantity': variant.available_quantity,
        }
        return JsonResponse(data)
    except ProductVariant.DoesNotExist:
        return JsonResponse({'error': 'Variant not found'}, status=404)

def product_detail(request, product_id):
    product = get_object_or_404(Products, id=product_id)

    product_images = ProductImage.objects.filter(product=product)
    variants = product.variants.all()
    wishlist = None

    if request.user.is_authenticated:
        wishlist = WishlistItem.objects.filter(wishlist__user=request.user, product=product).exists()

    context = {
        'product': product,  # Fix key name
        'discounted_price': product.discounted_price(),  # Corrected method usage
        'product_images': product_images,
        'variants': variants,
        'wishlist': wishlist,
    }
    return render(request, 'product_detail.html', context)

@never_cache
def password(request):
    if request.user.is_authenticated:
        return redirect('homepage')

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirmpassword')
        
        username = request.session.get('reset_username')

        if not username:
            messages.error(request, "Session expired or invalid request.")
            return redirect('login')

        try:
            user = User.objects.get(username=username)
            if not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password):
                messages.error(request, 'Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character.')
                return redirect('password')
            if password == confirm_password:
                user.set_password(password)
                user.save()

                update_session_auth_hash(request, user)

                messages.success(request, 'Password updated successfully!')
                return redirect('login') 
            else:
                messages.error(request, 'Passwords do not match.')
                return redirect('password')

        except User.DoesNotExist:
            messages.error(request, 'User does not exist.')
            return redirect('password')

    return render(request, 'password.html')

@login_required
def wishlist_view(request):
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        wishlist_items = WishlistItem.objects.filter(wishlist=wishlist).select_related('product')
    except Wishlist.DoesNotExist:
        wishlist_items = []

    context = {
        'wishlist_items': wishlist_items
    }
    return render(request, 'wishlist.html', context)

@login_required(login_url='/login/')
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Products, id=product_id)
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    wishlist_item = WishlistItem.objects.filter(wishlist=wishlist, product=product)


    if wishlist_item.exists():
        wishlist_item.delete()
        messages.success(request, f"{product.name} removed from your wishlist")
    else:
        WishlistItem.objects.create(wishlist=wishlist, product=product)
        messages.success(request, f"{product.name} added to your wishlist")

    # Redirect back to previous page
    next_url = request.GET.get('next', reverse('product_detail', args=[product_id]))
    return redirect(next_url)

@login_required
def remove_from_wishlist(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Products, id=product_id)
        wishlist = get_object_or_404(Wishlist, user=request.user)
        
        try:
            wishlist_item = WishlistItem.objects.get(wishlist=wishlist, product=product)
            wishlist_item.delete()
            messages.success(request, f"{product.name} removed from your wishlist")
        except WishlistItem.DoesNotExist:
            messages.error(request, "Item not found in wishlist")
    
    return redirect('wishlist_view')

# Views.py
@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    cart_items = CartItem.objects.select_related('product', 'variant').filter(cart=cart)
    
    subtotal = 0
    item_prices = {}
    item_weights = {}
    
    for item in cart_items:
        # Use the price_at_time field that already stores the discounted price
        item_total = item.price_at_time * item.quantity
        
        if item.variant:
            item_weight = item.variant.weight
        else:
            item_weight = 0 
        
        subtotal += item_total
        
        if item.quantity > 2:
            item_prices[item.product.name] = item_total 
            item_weights[item.product.name] = item_weight
    
    shipping_cost = 0 if subtotal > 499 else 50
    
    total = subtotal + shipping_cost
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'total': total,
        'item_prices': item_prices, 
        'item_weights': item_weights,
    }
    
    return render(request, 'cart.html', context)


@require_POST
def add_to_cart(request, product_id):
    if not request.user.is_authenticated:
        messages.error(request, 'You must be logged in to add items to the cart.')
        return redirect('login')

    try:
        product = get_object_or_404(Products, id=product_id)
        variant_id = request.POST.get('variant_id')

        if not variant_id:
            messages.error(request, 'Please select a variant.')
            return redirect('product_detail', product_id=product_id)

        variant = get_object_or_404(ProductVariant, id=variant_id, product=product)

        try:
            quantity = int(request.POST.get('quantity', 1))
            if quantity < 1:
                raise ValueError
        except ValueError:
            messages.error(request, 'Invalid quantity.')
            return redirect('product_detail', product_id=product_id)

        if quantity > variant.available_quantity:
            messages.error(request, f'Only {variant.available_quantity} items available in stock.')
            return redirect('product_detail', product_id=product_id)

        cart, created = Cart.objects.get_or_create(user=request.user)
        wishlist = Wishlist.objects.filter(user=request.user).first()
        if wishlist:
            WishlistItem.objects.filter(wishlist=wishlist, product=product).delete()

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            defaults={'quantity': 0}
        )

        # Update quantity
        cart_item.quantity += quantity
        cart_item.save()  # This will trigger the save method which sets price_at_time to discounted price

        messages.success(request, f'Added {quantity} {product.name} ({variant.get_weight_display()}) to cart.')
        return redirect('cart_view')

    except Exception as e:
        messages.error(request, 'An error occurred while adding to cart.')
        return redirect('product_detail', product_id=product_id)

@login_required
def update_cart_quantity(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        action = request.POST.get('action')

        # Get the cart item and ensure it belongs to the current user
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

        # Get the discounted price from the cart item
        item_price = cart_item.price_at_time

        # Check availability before incrementing
        if action == 'increment':
            max_available = cart_item.variant.available_quantity if cart_item.variant else cart_item.product.available_quantity
            if cart_item.quantity < max_available:
                cart_item.quantity += 1
            else:
                return JsonResponse({
                    'error': f'Only {max_available} items available in stock.'
                }, status=400)
        elif action == 'decrement':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1

        cart_item.save()

        # Recalculate subtotal, total
        cart_items = CartItem.objects.filter(cart=cart_item.cart)
        subtotal = sum(item.price_at_time * item.quantity for item in cart_items)
        shipping_cost = 0 if subtotal > 499 else 50
        total = subtotal + shipping_cost

        return JsonResponse({
            'quantity': cart_item.quantity,
            'item_price': float(item_price),
            'item_total_price': float(item_price * cart_item.quantity), 
            'subtotal': float(subtotal),
            'total': float(total),
            'shipping_cost': float(shipping_cost),
        })

# JavaScript for the template

@login_required
def remove_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, f'{cart_item.product.name} removed from cart.')
    return redirect('cart_view')

def category_products(request, category_name):
    category = get_object_or_404(Category, name=category_name)
    
    products = Products.objects.filter(category=category)
    for product in products:
        if product.discount:
            discount_amount = (product.price * product.discount) / 100  # Calculate discount
            product.discounted_price = product.price - discount_amount

    # Handle sorting
    sort_option = request.GET.get('sort', '')
    if sort_option == 'price_low':
        products = products.order_by('price')
    elif sort_option == 'price_high':
        products = products.order_by('-price')
    elif sort_option == 'name_asc':
        products = products.order_by('name')
    elif sort_option == 'newest':
        products = products.order_by('-created_at') 

    categories = Category.objects.all()

    context = {
        'categories': category,
        'products': products,
        'category': categories,
        'selected_sort': sort_option,
    }

    return render(request, 'category_products.html', context)

def profile_view(request):
    wallet, created = Wallet.objects.get_or_create(
        user=request.user,
        defaults={'balance': Decimal('0.00')}
    )

    active_tab = request.GET.get("tab", "profile") 

    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    addresses = Address.objects.filter(user=request.user)

    context = {
        'user': request.user,
        'addresses': addresses,
        'orders': orders,
        'wallet': wallet,
        'active_tab': active_tab,  
    }
    return render(request, 'profile.html', context)

@login_required
def order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_details.html', {'order': order})


def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'cancel':
            cancellation_reason = request.POST.get('reason', '').strip()
            if cancellation_reason:
                order.status = 'CANCELLED'
                order.cancellation_reason = cancellation_reason
                order.save()
                
                if order.payment.method != 'cod':
                    wallet, created = Wallet.objects.get_or_create(user=order.user, defaults={'balance': Decimal('0')})
                    wallet.balance += order.net_amount
                    wallet.save()

                    # refund
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        order=order,
                        amount=order.net_amount,
                        type='CREDIT'
                    )

                messages.success(request, 'Your order has been cancelled successfully.')
                return redirect('profile')
            else:
                messages.error(request, 'Please provide a reason for cancellation.')

        elif action == 'report':
            order_item_id = request.POST.get('order_item')
            description = request.POST.get('description', '').strip()
            image = request.FILES.get('image')

            if description and order_item_id:
                order_item = get_object_or_404(OrderItem, id=order_item_id)
                complaint = Complaint(order_item=order_item, description=description)
                if image:
                    complaint.image = image
                complaint.save()
                messages.success(request, 'Your complaint has been submitted successfully.')
                return redirect('profile')
            else:
                messages.error(request, 'Please provide a description and select a product.')

    return render(request, 'cancel_order.html', {'order': order})


@login_required
def address_create(request):
    if request.method == "POST":
        pincode = request.POST.get('pin_code')
        if not Store.objects.filter(pincode=pincode, is_active=True).exists():
                messages.error(request,'Devlivery service unavailable in this area')
                referer = request.META.get('HTTP_REFERER', 'profile')
                return redirect(referer)
        Address.objects.create(
            user=request.user,
            name=request.POST.get("name"),
            mobile_number=request.POST.get("mobile_number"),
            alternate_number=request.POST.get("alternate_number"),
            pin_code=request.POST.get("pin_code"),
            city=request.POST.get("city"),
            district=request.POST.get("district"),
            state=request.POST.get("state"),
            land_mark=request.POST.get("land_mark"),
            address_type=request.POST.get("address_type"),
        )
        messages.success(request, "Address added successfully!")
        referer = request.META.get('HTTP_REFERER', 'profile')
        return redirect(referer)

    return redirect("profile")

@login_required
def edit_profile(request):
    if request.method == 'POST':
        user = request.user
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone_no = request.POST.get('phone_no')
        profilee = request.FILES.get('profile')

        if not re.match(r'^\+?1?\d{9,15}$', phone_no):
            messages.error(request, 'Invalid phone number.')
            return redirect('profile')

        if email != user.email:
            otp_code = generate_otp()

            expires_at = timezone.now() + timedelta(minutes=5)

            otp = OTPVerification.objects.create(
                user=user,
                otp=otp_code,
                email_or_phone=email,  
                expires_at=expires_at
            )

            send_mail(
                'Verify Your New Email Address',
                f'Your OTP for changing your email is: {otp_code}',
                'your_email@example.com',  
                [email],
                fail_silently=False,
            )
            request.session['next_page'] = 'profile' 
            messages.info(request, 'An OTP has been sent to your new email. Please verify it.')
            return redirect('verify_otp') 

        user.first_name = name
        user.email = email
        user.phone_no = phone_no
        if profilee:
            user.profile = profilee
        user.save()

        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')  

    return render(request, 'profile.html')

def verify_otp(request):
    if request.method == 'POST':
        otp_code = request.POST.get('otp')

        try:
            otp_entry = OTPVerification.objects.get(otp=otp_code, verified=False)
            
            if otp_entry.is_expired():
                messages.error(request, 'OTP has expired. Please request a new OTP.')
                return redirect('forgot_password')

            # Mark OTP as verified
            otp_entry.verified = True
            otp_entry.save()

            # Get the user and mark as verified
            user = otp_entry.user
            if user:
                user.is_verify = True
                user.save() 

            messages.success(request, 'OTP verification successful!')

            # Determine the next page dynamically
            next_page = request.session.get('next_page', 'profile')
            del request.session['next_page']

            return redirect(next_page)
        
        except OTPVerification.DoesNotExist:
            messages.error(request, 'Invalid OTP. Please try again.')
            return redirect('verify_otp')

    return render(request, 'verify_otp.html')

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

@login_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('profile')

        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('profile')

        request.user.set_password(new_password)
        request.user.save()

        update_session_auth_hash(request, request.user)

        messages.success(request, 'Password changed successfully!')
        return redirect('profile') 

    return redirect('profile')

@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == 'POST':
        address.name = request.POST.get('name')
        address.pin_code = request.POST.get('pin_code')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.district = request.POST.get('district')
        address.address_type = request.POST.get('address_type')
        address.land_mark = request.POST.get('land_mark', '')
        address.mobile_number = request.POST.get('mobile_number')
        address.alternate_number = request.POST.get('alternate_number', '')
        address.save()
        messages.success(request, 'Address updated successfully!')
        return redirect('profile')
    
    return redirect('profile')


@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    if request.method == 'POST':
        try:
            address.delete()
            messages.success(request, "Address deleted successfully!")
        except ProtectedError:
            messages.error(request, "This address is linked to an order and cannot be deleted.")
    else:
        messages.error(request, "Invalid request.")
    referer = request.META.get('HTTP_REFERER', 'profile')
    return redirect(referer)

@login_required
def checkout(request):
    if request.method == 'POST':
        try:
            address_id = request.POST.get('selected_address')
            payment_method = request.POST.get('paymentMethod')
            pending_coupon = request.session.get('pending_coupon')
            discount = Decimal('0')
            coupon = None

            if not address_id:
                return JsonResponse({'error': 'Please select an address'}, status=400)

            address = Address.objects.filter(id=address_id, user=request.user).first()
            if not address:
                return JsonResponse({'error': 'Invalid address'}, status=400)

            if not Store.objects.filter(pincode=address.pin_code, is_active=True).exists():
                messages.error(request, 'Delivery service unavailable in this area')
                return redirect('checkout')

            try:
                cart = Cart.objects.get(user=request.user)
                cart_items = CartItem.objects.filter(cart=cart).select_related('product', 'variant')
                if not cart_items.exists():
                    return JsonResponse({'error': 'Cart is empty'}, status=400)

                # Calculate subtotal and shipping charge
                subtotal = sum(item.price_at_time * item.quantity for item in cart_items)
                shipping_charge = 0 if subtotal > 499 else 50
                total_amount = subtotal + shipping_charge

                # Apply coupon if available
                if pending_coupon:
                    coupon_code = pending_coupon.get('code')
                    discount = Decimal(pending_coupon.get('discount', '0'))
                    try:
                        coupon = Coupon.objects.get(
                            code=coupon_code,
                            is_active=True,
                            expire_date__gt=timezone.now()
                        )
                        existing_usage = CouponUsage.objects.filter(user=request.user, coupon=coupon).first()
                        if existing_usage and existing_usage.limit >= coupon.limit:
                            return JsonResponse({'error': 'Coupon usage limit reached'}, status=400)
                        total_amount -= discount  # Apply discount after validation
                    except Coupon.DoesNotExist:
                        return JsonResponse({'error': 'Invalid coupon code'}, status=400)

                # Check stock availability
                for item in cart_items:
                    if item.quantity > item.product.available_quantity:
                        messages.error(request, f'Out of stock: {item.product.name}')
                        return redirect('cart_view')

                if payment_method == 'cod':
                    if total_amount > 1000:
                        return JsonResponse({'error': 'COD not available for orders over ₹1000'}, status=400)
                    with transaction.atomic():
                        payment = Payment.objects.create(
                            user=request.user,
                            amount=total_amount,
                            status='PENDING',
                            method=payment_method,
                            date=timezone.now(),
                            coupon=coupon,
                        )
                        order = create_order(
                            user=request.user,
                            address_id=address_id,
                            total=subtotal,
                            shipping_charge=shipping_charge,
                            cart_items=cart_items,
                            coupon=coupon,
                            discount=discount,
                            payment=payment,
                            status='PENDING',
                            net_amount=total_amount
                        )
                        payment.order = order
                        payment.save()

                        Transaction.objects.create(
                            payment=payment,
                            status='PENDING',
                            amount=total_amount,
                            date=timezone.now()
                        )

                        for item in cart_items:
                            item.product.available_quantity -= item.quantity
                            item.product.save()
                        cart_items.delete()
                        request.session.pop('pending_coupon', None)
                        return JsonResponse({'status': 'success', 'redirect_url': reverse('order_success')})

                elif payment_method == 'wallet':
                    try:
                        wallet = Wallet.objects.get(user=request.user)
                        if wallet.balance < total_amount:
                            return JsonResponse({'error': 'Insufficient wallet balance'}, status=400)
                        with transaction.atomic():
                            payment = Payment.objects.create(
                                user=request.user,
                                amount=total_amount,
                                status='SUCCESS',
                                method='wallet',
                                date=timezone.now(),
                                coupon=coupon,
                                wallet=wallet
                            )
                            wallet.balance -= total_amount
                            wallet.save()

                            order = create_order(
                                user=request.user,
                                address_id=address_id,
                                total=subtotal,
                                shipping_charge=shipping_charge,
                                cart_items=cart_items,
                                coupon=coupon,
                                discount=discount,
                                payment=payment,
                                status='CONFIRMED',
                                net_amount=total_amount
                            )
                            payment.order = order
                            payment.save()

                            WalletTransaction.objects.create(
                                wallet=wallet,
                                order=order,
                                amount=total_amount,
                                type='DEBIT'
                            )

                            Transaction.objects.create(
                                payment=payment,
                                status='SUCCESS',
                                amount=total_amount,
                                date=timezone.now()
                            )

                            for item in cart_items:
                                item.product.available_quantity -= item.quantity
                                item.product.save()
                            cart_items.delete()
                            request.session.pop('pending_coupon', None)
                            return JsonResponse({'status': 'success', 'redirect_url': reverse('order_success')})
                    except Wallet.DoesNotExist:
                        return JsonResponse({'error': 'No wallet found for this account'}, status=400)

                elif payment_method in ['creditCard', 'debitCard']:
                    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                    razorpay_order = client.order.create({
                        'amount': int(total_amount * 100),
                        'currency': 'INR',
                        'payment_capture': '1'
                    })
                    with transaction.atomic():
                        payment = Payment.objects.create(
                            user=request.user,
                            amount=total_amount,
                            status='PENDING',
                            method=payment_method,
                            date=timezone.now(),
                            coupon=coupon,
                            razorpay_order_id=razorpay_order['id']
                        )
                        order = create_order(
                            user=request.user,
                            address_id=address_id,
                            total=subtotal,
                            shipping_charge=shipping_charge,
                            cart_items=cart_items,
                            coupon=coupon,
                            discount=discount,
                            payment=payment,
                            status='PENDING',
                            net_amount=total_amount
                        )
                        Transaction.objects.create(
                            payment=payment,
                            status='PENDING',
                            amount=total_amount,
                            date=timezone.now()
                        )
                        return JsonResponse({
                            'status': 'success',
                            'razorpay_order_id': razorpay_order['id'],
                            'amount': int(total_amount * 100),
                            'currency': 'INR'
                        })
                else:
                    return JsonResponse({'error': 'Invalid payment method'}, status=400)

            except Cart.DoesNotExist:
                return JsonResponse({'error': 'Your cart is empty'}, status=400)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart).select_related('product', 'variant')
        addresses = Address.objects.filter(user=request.user)
        wallet = Wallet.objects.get(user=request.user)

        if not cart_items.exists():
            messages.error(request, 'Your cart is empty')
            return redirect('cart_view')

        
        subtotal = sum(item.price_at_time * item.quantity for item in cart_items)
        shipping_charge = 0 if subtotal > 499 else 50
        total_amount = subtotal + shipping_charge

        context = {
            'addresses': addresses,
            'cart_items': cart_items,
            'subtotal': subtotal,
            'shipping_charge': shipping_charge,
            'total_amount': total_amount,
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'wallet_balance': wallet,
        }
        return render(request, 'checkout.html', context)
    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty')
        return redirect('cart_view')


def create_order(user, address_id, total, shipping_charge, cart_items, coupon, discount=None, payment=None, net_amount=0,status='PENDING'):
    with transaction.atomic():
        order = Order.objects.create(
            user=user,
            payment=payment,
            address_id=address_id,
            total=total,
            status=status,
            order_date=timezone.now(),
            shipping_chrg=shipping_charge,
            net_amount=net_amount,
            coupon=coupon,
            discount=discount or 0 
        )
        for item in cart_items:
            price = item.variant.price if item.variant else item.product.price
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                variant=item.variant,
                total_amount = sum(item.price_at_order * item.quantity for item in order.items.all())
            )

        send_mail(
            subject="Order Confirmation - Fresh 2 Home",
            message=(
                f"Dear {user.username},\n\n"
                f"Your order #{order.id} has been placed with a pending payment status.\n"
                f"Total: ₹{total}\n"
                f"Payment Method: {payment.method if payment else 'N/A'}\n\n"
                f"We will update you once the payment is confirmed.\n\n"
                f"Thank you for shopping with us!"
            ),
            from_email='support@fresh2home.com',
            recipient_list=[user.email],
            fail_silently=False,
        )

        if coupon:
            try:
                coupon_usage, created = CouponUsage.objects.get_or_create(
                    user=user,
                    coupon=coupon,
                    defaults={'limit': 1}
                )
                if not created:
                    coupon_usage.limit += 1
                    coupon_usage.save()
            except Coupon.DoesNotExist:
                pass

        if user.referred_by and Order.objects.filter(user=user).count() == 1:
            referrer = user.referred_by
            wallet, created = Wallet.objects.get_or_create(user=referrer, defaults={'balance': Decimal('50')})
            if not created:
                wallet.balance += Decimal('1000')
                wallet.save()
            WalletTransaction.objects.create(
                wallet=wallet,
                order=order,
                amount=Decimal('1000'),
                type='CREDIT'
            )

        return order


@csrf_exempt
def razorpay_callback(request):
    if request.method == "POST":
        try:
            payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
            transaction = Transaction.objects.get(payment=payment)

            try:
                client.utility.verify_payment_signature(params_dict)
                payment.status = 'SUCCESS'
                payment.razorpay_order_id = razorpay_order_id
                payment.razorpay_payment_id = payment_id
                payment.razorpay_signature = signature
                transaction.status='SUCCESS'
                transaction.save()
                verified = True
            except Exception as e:
                payment.status = 'FAILED'
                transaction.status='FAILED'
                verified = False
                transaction.save()
            payment.save()

            # Retrieve the order linked to this payment.
            order = Order.objects.get(payment=payment)
            if verified:   
                order.status = 'CONFIRMED'
                order.save()
                
                # Reduce stock and clear cart items upon successful payment.
                cart = Cart.objects.get(user=payment.user)
                cart_items = CartItem.objects.filter(cart=cart).select_related('product', 'variant')
                for item in cart_items:
                    item.product.available_quantity -= item.quantity
                    item.product.save()
                cart_items.delete()

                return HttpResponseRedirect(reverse('order_success'))
            else:
                order.status = 'FAILED'
                order.save()
                transaction.status='FAILED'
                transaction.save()
                messages.error(request, 'Payment failed. Order status updated to FAILED.')
                return HttpResponseRedirect(reverse('checkout'))

        except Exception as e:
            messages.error(request, 'An error occurred during payment processing.')
            return HttpResponseRedirect(reverse('checkout'))
    messages.error(request, 'Invalid request method.')
    return HttpResponseRedirect(reverse('checkout'))

@require_POST
@login_required
def initiate_repayment_ajax(request, order_id):

    try:
        # Retrieve the order and its payment record (ensure order belongs to the user)
        order = get_object_or_404(Order, id=order_id, user=request.user)
        payment = order.payment

        # Only allow repayment for credit/debit card orders that are not successful
        if payment.method not in ['creditCard', 'debitCard'] or payment.status == 'SUCCESS':
            return JsonResponse({'status': 'error', 'message': 'This order is not eligible for repayment.'})

        # Create a new Razorpay order using the order total (assumed in INR)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        amount = int(order.total * 100)  # Convert rupees to paise
        razorpay_order = client.order.create({
            'amount': amount,
            'currency': 'INR',
            'payment_capture': '1'
        })

        # Update the payment record with the new Razorpay order ID and reset status to PENDING
        payment.razorpay_order_id = razorpay_order['id']
        payment.status = 'PENDING'
        payment.save()

        return JsonResponse({
            'status': 'success',
            'id': razorpay_order['id'],
            'amount': amount,
            'currency': 'INR'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@require_POST
@login_required
def ajax_razorpay_callback(request):

    try:
        data = json.loads(request.body)
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')
        order_id = data.get('order_id')

        # Retrieve the order and its payment record
        order = get_object_or_404(Order, id=order_id, user=request.user)
        payment = order.payment

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        try:
            # Verify payment signature
            client.utility.verify_payment_signature(params_dict)
            payment.status = 'SUCCESS'
            payment.razorpay_order_id = razorpay_order_id
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.save()

            order.status = 'CONFIRMED'
        except Exception as e:
            payment.status = 'FAILED'
            order.status = 'FAILED'
        payment.save()
        order.save()

        # If payment is successful, reduce product quantity and clear cart items
        if payment.status == 'SUCCESS':
            from .models import Cart, CartItem  # Import models locally if needed
            try:
                cart = Cart.objects.get(user=request.user)
                cart_items = CartItem.objects.filter(cart=cart).select_related('product', 'variant')
                for item in cart_items:
                    product = item.product
                    product.available_quantity -= item.quantity
                    product.save()
                cart_items.delete()
            except Cart.DoesNotExist:
                pass

            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Payment verification failed.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def apply_coupon(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        coupon_code = data.get('coupon_code')
        subtotall = data.get('subtotal')
        shipping_chargee = data.get('shipping_charge')

        subtotal = Decimal(subtotall)
        shipping_charge = Decimal(shipping_chargee)

        try:
            coupon = Coupon.objects.get(
                code=coupon_code, 
                is_active=True, 
                expire_date__gt=timezone.now()
            )

            existing_usage = CouponUsage.objects.filter(
                user=request.user, 
                coupon=coupon
            ).first()

            if existing_usage and existing_usage.limit >= coupon.limit:
                return JsonResponse({
                    'success': False, 
                    'message': 'Coupon usage limit reached.'
                })

            if coupon.type == 'PERCENTAGE':
                discount = (Decimal(coupon.discount_value) / Decimal(100)) * subtotal
            else: 
                discount = Decimal(coupon.discount_value)

            if discount > subtotal:
                discount = subtotal

            total_amount = subtotal + shipping_charge - discount

            request.session['pending_coupon'] = {
                'code': coupon_code,
                'discount': str(discount)  # Convert Decimal to string for session storage
            }

            return JsonResponse({
                'success': True,
                'discount': float(discount),
                'total_amount': float(total_amount) 
            })

        except Coupon.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'Invalid coupon code.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'message': str(e)
            })

    return JsonResponse({
        'success': False, 
        'message': 'Invalid request method.'
    })

def order_success(request):
    return render(request,'order_success.html')

def download_invoice(request,order_id):
    order = get_object_or_404(Order, id=order_id)
    template_path = 'invoice_template.html'
    context = {'order': order}
    template = get_template(template_path)
    html = template.render(context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="invoice.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse("Error while generating PDF", status=500)
    
    return response

@login_required
@csrf_protect
@require_POST
def add_money(request):
    try:
        # Parse JSON data
        data = json.loads(request.body)
        
        # Validate amount
        amount = Decimal(data.get('amount', 0))
        if amount <= 0:
            return JsonResponse({
                'error': 'Invalid amount. Amount must be greater than zero.'
            }, status=400)

        # Convert to paise
        amount_in_paise = int(amount * 100)

        # Create Razorpay client
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        # Create payment order
        payment_order = client.order.create({
            'amount': amount_in_paise, 
            'currency': 'INR', 
            'payment_capture': '1'
        })

        # Store order details temporarily in session
        request.session['wallet_top_up_amount'] = float(amount)
        request.session['razorpay_order_id'] = payment_order['id']

        return JsonResponse({
            'id': payment_order['id'],
            'amount': payment_order['amount'],
            'currency': payment_order['currency']
        })

    except (ValueError, TypeError, KeyError) as e:
        return JsonResponse({
            'error': f'Invalid input: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Unexpected error: {str(e)}'
        }, status=500)

@login_required
@csrf_protect
@require_POST
def payment_callback(request):
    try:
        # Parse JSON data
        data = json.loads(request.body)
        
        # Retrieve Razorpay payment details
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')

        # Verify session data
        session_order_id = request.session.get('razorpay_order_id')
        session_amount = request.session.get('wallet_top_up_amount')

        if not session_order_id or not session_amount:
            return JsonResponse({
                'status': 'error', 
                'message': 'Invalid session data'
            }, status=400)

        # Verify payment with Razorpay
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        
        # Verify payment signature
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })

        # Convert amount to Decimal
        amount_decimal = Decimal(str(session_amount))

        # Get or create user wallet
        wallet, _ = Wallet.objects.get_or_create(
            user=request.user, 
            defaults={'balance': Decimal('0.00')}
        )

        # Update wallet balance
        wallet.balance += amount_decimal
        wallet.save()

        # Create wallet transaction
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount_decimal,
            type='CREDIT'
        )

        # Clear session data
        del request.session['wallet_top_up_amount']
        del request.session['razorpay_order_id']

        return JsonResponse({
            'status': 'success', 
            'message': f'₹{amount_decimal} added to wallet successfully'
        })

    except Exception as e:
        # Log the error
        return JsonResponse({
            'status': 'error', 
            'message': 'Failed to add money to wallet'
        }, status=500)

def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get('email')

        # Check if user exists with the given email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No account found with this email.")
            return render(request, "forgot_password.html")

        otp = generate_otp()
        otp_expiry_time = timezone.now() + timedelta(minutes=5)

        send_mail(
            'Your OTP for Password Reset',
            f'Your OTP is {otp}. It will expire in 5 minutes.',
            'fresh2home@example.com',
            [email],
            fail_silently=False,
        )

        OTPVerification.objects.create(
            user=user,
            otp=otp,
            email_or_phone=email,
            expires_at=otp_expiry_time
        )
        request.session['reset_username'] = user.username

        request.session['next_page'] = 'password' 

        return redirect("verify_otp")

    return render(request, "forgot_password.html")


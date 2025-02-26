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
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
import random
from django.core.mail import send_mail
from django.http import HttpResponse
from django.db import transaction
import re,json
from django.template.loader import render_to_string
# from weasyprint import HTML
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import ProtectedError
from django.contrib.auth import logout
import razorpay,uuid
from reportlab.pdfgen import canvas
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.contrib.auth.forms import PasswordResetForm



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
    print(referrer)
    
    # Store the referrer's ID in the session
    request.session['referrer_id'] = referrer.referral_id
    print(request.session['referrer_id'])
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
        pincode = request.POST['pincode']
        referral_id = generate_referral_id(username)

        # Check if the user is referred
        referrer_id = request.session.get('referrer_id')
        if referrer_id:
            referrer = User.objects.get(referral_id=referrer_id)
            del request.session['referrer_id']
        else:
            referrer = None

        # Validate user input
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
        if not Store.objects.filter(pincode=pincode).exists():
            messages.error(request,'Delivery is not available in this place!')

        # Generate OTP
        otp = generate_otp()
        otp_expiry_time = timezone.now() + timedelta(minutes=5)
        print(otp)
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
            referral_id=referral_id,
            referred_by=referrer  # Save the referrer
        )
        
        # Create OTP record
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
def loading_page(request):
    products = Products.objects.prefetch_related('images')
    category = Category.objects.all()
    banners = Banner.objects.all()
    context = {
        'products': products,
        'category': category,
        'banners': banners
    }
    return render(request,'home_page.html',context)

@never_cache
@login_required(login_url='signin') 
def homepage(request):
    if request.user.is_superuser:
        return redirect('adminlogin')
    
    products = Products.objects.prefetch_related('images')
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
        result = result.order_by("-created_at")  # Assuming 'created_at' exists

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
            'price': float(variant.price),
            'available_quantity': variant.available_quantity,
        }
        return JsonResponse(data)
    except ProductVariant.DoesNotExist:
        return JsonResponse({'error': 'Variant not found'}, status=404)

def product_detail(request, product_id):
    product = get_object_or_404(Products, id=product_id)
    product_images = ProductImage.objects.filter(product=product)
    variants = product.variants.all()
    wishlist = WishlistItem.objects.filter(wishlist__user = request.user,product__id=product_id).exists()
    context = {
        'product': product,
        'product_images': product_images,
        'variants': variants,
        'wishlist': wishlist
    }
    return render(request, 'product_detail.html', context)

@never_cache
def password(request):
    if request.user.is_authenticated:
        return redirect('homepage')  # Redirect if user is already logged in

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirmpassword')
        
        # Assuming you store username/email in session for password reset
        username = request.session.get('reset_username')  # Ensure it's stored somewhere

        if not username:
            messages.error(request, "Session expired or invalid request.")
            return redirect('login')

        try:
            user = User.objects.get(username=username)

            if password == confirm_password:
                user.set_password(password)  # Proper way to update password
                user.save()

                # Ensure the user stays logged in after changing the password
                update_session_auth_hash(request, user)

                messages.success(request, 'Password updated successfully!')
                return redirect('login')  # Redirect to login page after password reset
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

@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Products, id=product_id)
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    wishlist_item = WishlistItem.objects.filter(wishlist=wishlist, product=product)


    if wishlist_item.exists():
        # Remove from wishlist if already exists
        wishlist_item.delete()
        messages.success(request, f"{product.name} removed from your wishlist")
    else:
        # Add to wishlist
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

@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    cart_items = CartItem.objects.select_related('product', 'variant').filter(cart=cart)
    
    subtotal = 0
    item_prices = {}
    item_weights = {}
    
    for item in cart_items:
        if item.variant:  # Check if variant exists
            item_total = item.variant.price * item.quantity
            item_weight = item.variant.weight
        else:
            item_total = item.product.price * item.quantity  # Use product price if no variant
            item_weight = 0  # Set item weight to 0 if no variant
        
        subtotal += item_total
        
        if item.quantity > 2:  # Show item price only for items with quantity > 2
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

        # Validate quantity
        try:
            quantity = int(request.POST.get('quantity', 1))
            if quantity < 1:
                raise ValueError
        except ValueError:
            messages.error(request, 'Invalid quantity.')
            return redirect('product_detail', product_id=product_id)

        # Check stock availability
        if quantity > variant.available_quantity:
            messages.error(request, f'Only {variant.available_quantity} items available in stock.')
            return redirect('product_detail', product_id=product_id)

        # Get or create the cart for the user
        cart, created = Cart.objects.get_or_create(user=request.user)
        wishlist = Wishlist.objects.filter(user=request.user).first()
        if wishlist:
            WishlistItem.objects.filter(wishlist=wishlist, product=product).delete()

        # Get or create the cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            defaults={'quantity': 0}
        )

        # Update quantity
        cart_item.quantity += quantity
        cart_item.save()

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

        # Determine the price based on the variant (if it exists) or the product
        item_price = cart_item.variant.price if cart_item.variant else cart_item.product.price

        # Update quantity based on action
        if action == 'increment':
            if cart_item.quantity < cart_item.product.available_quantity:
                cart_item.quantity += 1
        elif action == 'decrement':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1

        cart_item.save()

        # Recalculate subtotal, total, and individual item price
        cart_items = CartItem.objects.filter(cart=cart_item.cart)
        subtotal = sum(
            (item.variant.price if item.variant else item.product.price) * item.quantity
            for item in cart_items
        )
        shipping_cost = 0 if subtotal > 499 else 50
        total = subtotal + shipping_cost

        return JsonResponse({
            'quantity': cart_item.quantity,
            'item_price': float(item_price),  # Send the correct price (variant or product)
            'item_total_price': float(item_price * cart_item.quantity),  # Use item_price
            'subtotal': float(subtotal),
            'total': float(total),
            'shipping_cost': float(shipping_cost),
        })

@login_required
def remove_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, f'{cart_item.product.name} removed from cart.')
    return redirect('cart_view')

def category_products(request, category_name):
    category = get_object_or_404(Category, name=category_name)
    
    products = Products.objects.filter(category=category)

    # Handle sorting
    sort_option = request.GET.get('sort', '')
    if sort_option == 'price_low':
        products = products.order_by('price')
    elif sort_option == 'price_high':
        products = products.order_by('-price')
    elif sort_option == 'name_asc':
        products = products.order_by('name')
    elif sort_option == 'newest':
        products = products.order_by('-created_at')  # Assuming you have a 'created_at' field

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
                messages.success(request, 'Your order has been cancelled successfully.')
                return redirect('profile')  # Redirect to order detail page
            else:
                messages.error(request, 'Please provide a reason for cancellation.')

        elif action == 'report':
            order_item_id = request.POST.get('order_item')
            description = request.POST.get('description', '').strip()
            image = request.FILES.get('image')  # Handle image upload if needed

            if description and order_item_id:
                order_item = get_object_or_404(OrderItem, id=order_item_id)
                complaint = Complaint(order_item=order_item, description=description)
                if image:
                    complaint.image = image  # Assuming you have an image field in the Complaint model
                complaint.save()
                messages.success(request, 'Your complaint has been submitted successfully.')
                return redirect('profile')  # Redirect to order detail page
            else:
                messages.error(request, 'Please provide a description and select a product.')

    return render(request, 'cancel_order.html', {'order': order})


@login_required
def address_create(request):
    if request.method == "POST":
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
            print(otp_code)

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
                return redirect('forgot_password')  # Redirect to the OTP request page

            # Mark OTP as verified
            otp_entry.verified = True
            otp_entry.save()

            # Get the user and mark as verified
            user = otp_entry.user
            if user:
                user.is_verify = True  # Only verify if OTP is correct
                user.save()  # Save the updated user instance

            messages.success(request, 'OTP verification successful!')

            # Determine the next page dynamically
            next_page = request.session.get('next_page', 'profile')  # Default to profile page
            del request.session['next_page']  # Clear session variable after use

            return redirect(next_page)
        
        except OTPVerification.DoesNotExist:
            messages.error(request, 'Invalid OTP. Please try again.')
            return redirect('verify_otp')

    return render(request, 'verify_otp.html')


# def verify_otp1(request):
#     if request.method == 'POST':
#         otp_code = request.POST.get('otp')

#         try:
#             otp_entry = OTPVerification.objects.get(otp=otp_code, verified=False)
            
#             if otp_entry.is_expired():
#                 messages.error(request, 'OTP has expired. Please request a new OTP.')
#                 return redirect('login') 

#             otp_entry.verified = True
#             otp_entry.save()

#             user = otp_entry.user
#             user.is_verify = True
#             user.email = otp_entry.email_or_phone 
#             user.save()

#             messages.success(request, 'Account created successfully! Please check your email for the OTP.')
#             return redirect('login') 

#         except OTPVerification.DoesNotExist:
#             messages.error(request, 'Invalid OTP. Please try again.')
#             return redirect('verify_otp1')  

#     # ✅ Fix: Return a response for GET requests
#     return render(request, 'verify_otp.html')

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
        return redirect('profile', {'active_tab': 'profile'})
    
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
            
            # Get pending coupon from session (if any)
            pending_coupon = request.session.get('pending_coupon')
            coupon_code = None
            discount = Decimal('0')
            
            if not address_id:
                return JsonResponse({'error': 'Please select an address'}, status=400)

            address = Address.objects.filter(id=address_id).first()
            if not address:
                return JsonResponse({'error': 'Invalid address'}, status=400)

            if not Store.objects.filter(pincode=address.pin_code, is_active=True).exists():
                return JsonResponse({'error': 'Service unavailable in this area'}, status=400)

            try:
                cart = Cart.objects.get(user=request.user)
                cart_items = CartItem.objects.filter(cart=cart).select_related('product', 'variant')

                if not cart_items.exists():
                    return JsonResponse({'error': 'Cart is empty'}, status=400)

                subtotal = sum(
                    (item.variant.price if item.variant else item.product.price) * item.quantity
                    for item in cart_items
                )
                print("Subtotal:", subtotal)
                shipping_charge = 0 if subtotal > 499 else 50
                print("Shipping Charge:", shipping_charge)
                
                # Handle coupon if present
                if pending_coupon:
                    coupon_code = pending_coupon.get('code')
                    discount = Decimal(pending_coupon.get('discount', '0'))
                    
                    # Validate coupon again
                    try:
                        coupon = Coupon.objects.get(
                            code=coupon_code,
                            is_active=True,
                            expire_date__gt=timezone.now()
                        )
                        
                        # Check usage limit
                        existing_usage = CouponUsage.objects.filter(
                            user=request.user,
                            coupon=coupon
                        ).first()
                        
                        if existing_usage and existing_usage.limit >= coupon.limit:
                            return JsonResponse({
                                'error': 'Coupon usage limit reached'
                            }, status=400)
                            
                    except Coupon.DoesNotExist:
                        return JsonResponse({
                            'error': 'Invalid coupon code'
                        }, status=400)

                total_amount = subtotal + shipping_charge - discount

                # Check stock availability for each item
                for item in cart_items:
                    if item.quantity > item.product.available_quantity:
                        messages.error(request, f'Out of stock: {item.product.name}')
                        return redirect('cart_view')

                # Handle different payment methods
                if payment_method == 'cod':
                    if total_amount > 1000:
                        return JsonResponse({'error': 'COD not available for orders over ₹1000'}, status=400)

                    try:
                        with transaction.atomic():
                            order = create_order(
                                user=request.user,
                                address_id=address_id,
                                total=total_amount,
                                shipping_charge=shipping_charge,
                                cart_items=cart_items,
                                coupon_code=coupon_code,
                                discount=discount,
                                payment=None,
                                net_amount=total_amount
                            )

                            # Reduce stock and clear cart
                            for item in cart_items:
                                item.product.available_quantity -= item.quantity
                                item.product.save()

                            cart_items.delete()

                            # Clear the pending coupon from session if exists
                            if 'pending_coupon' in request.session:
                                del request.session['pending_coupon']

                            return JsonResponse({
                                'status': 'success',
                                'redirect_url': reverse('order_success')
                            })

                    except Exception as e:
                        print(f"COD Order Error: {str(e)}")
                        return JsonResponse({
                            'status': 'error',
                            'message': 'An error occurred while processing your order.'
                        }, status=400)

                elif payment_method == 'wallet':
                    try:
                        # Get user's wallet
                        wallet = Wallet.objects.get(user=request.user)
                        
                        # Check if wallet has sufficient balance
                        if wallet.balance < total_amount:
                            return JsonResponse({
                                'error': 'Insufficient wallet balance',
                                'current_balance': str(wallet.balance),
                                'required_amount': str(total_amount)
                            }, status=400)
                        
                        with transaction.atomic():
                            # Create payment record
                            payment = Payment.objects.create(
                                user=request.user,
                                amount=total_amount,
                                status='CONFIRMED',  # Wallet payments complete immediately
                                method='wallet',
                                date=timezone.now()
                            )
                            
                            # Deduct from wallet
                            wallet.balance -= total_amount
                            wallet.save()
                            
                            # Create wallet transaction
                            WalletTransaction.objects.create(
                                wallet=wallet,
                                order=None,  # Will be updated after order creation
                                amount=total_amount,
                                type='DEBIT'
                            )
                            
                            # Create order
                            order = create_order(
                                user=request.user,
                                address_id=address_id,
                                total=total_amount,
                                shipping_charge=shipping_charge,
                                cart_items=cart_items,
                                coupon_code=coupon_code,
                                discount=discount,
                                payment=payment,
                                net_amount=total_amount
                            )
                            
                            # Update wallet transaction with order reference
                            WalletTransaction.objects.filter(
                                wallet=wallet,
                                order=None,
                                type='DEBIT'
                            ).update(order=order)
                            
                            # Reduce stock and clear cart
                            for item in cart_items:
                                item.product.available_quantity -= item.quantity
                                item.product.save()
                            
                            cart_items.delete()
                            
                            # Clear the pending coupon from session if exists
                            if 'pending_coupon' in request.session:
                                del request.session['pending_coupon']
                            
                            return JsonResponse({
                                'status': 'success',
                                'redirect_url': reverse('order_success')
                            })
                    
                    except Wallet.DoesNotExist:
                        return JsonResponse({'error': 'No wallet found for this account'}, status=400)
                    except Exception as e:
                        print(f"Wallet Payment Error: {str(e)}")
                        return JsonResponse({
                            'status': 'error',
                            'message': 'An error occurred while processing your wallet payment.'
                        }, status=400)

                elif payment_method in ['creditCard', 'debitCard']:
                    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

                    razorpay_order = client.order.create({
                        'amount': int(total_amount * 100),  # Razorpay accepts amount in paise
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
                            razorpay_order_id=razorpay_order['id']
                        )

                        order = create_order(
                            user=request.user,
                            address_id=address_id,
                            total=total_amount,
                            shipping_charge=shipping_charge,
                            cart_items=cart_items,
                            coupon_code=coupon_code,
                            discount=discount,
                            payment=payment,
                            net_amount=total_amount
                        )

                        # Reduce stock and clear cart
                        for item in cart_items:
                            item.product.available_quantity -= item.quantity
                            item.product.save()
                        
                        cart_items.delete()

                        # Clear the pending coupon from session if exists
                        if 'pending_coupon' in request.session:
                            del request.session['pending_coupon']

                        return JsonResponse({
                            'status': 'success',
                            'razorpay_order_id': razorpay_order['id'],
                            'amount': int(total_amount * 100),
                            'currency': 'INR',
                            'order_id': order.id
                        })

                else:
                    return JsonResponse({'error': 'Invalid payment method'}, status=400)

            except Cart.DoesNotExist:
                return JsonResponse({'error': 'Your cart is empty'}, status=400)

        except Exception as e:
            print(f"Checkout Error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    # GET Request - Render Checkout Page
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart).select_related('product', 'variant')
        addresses = Address.objects.filter(user=request.user)
        wallet = Wallet.objects.get(user=request.user)

        if not cart_items.exists():
            messages.error(request, 'Your cart is empty')
            return redirect('cart_view')

        subtotal = sum(
            (item.variant.price if item.variant else item.product.price) * item.quantity
            for item in cart_items
        )
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


def create_order(user, address_id, total, shipping_charge, cart_items, coupon_code, discount=None, payment=None, net_amount=0):
    with transaction.atomic():
        order = Order.objects.create(
            user=user,
            payment=payment,
            address_id=address_id,
            total=total,
            status='PENDING',
            order_date=timezone.now(),
            shipping_chrg=shipping_charge,
            net_amount=net_amount,
            coupon_code=coupon_code,
            discount=discount or 0 
        )
        print('-------------------------------')
        # Create order items (use variant price if available)
        for item in cart_items:
            price = item.variant.price if item.variant else item.product.price
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                variant=item.variant,
                total_amount=price * item.quantity
            )

        # If coupon was used, update the usage record
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code)
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

        # Reward the referrer if this is the user's first order
        if user.referred_by and Order.objects.filter(user=user).count() == 1:
            referrer = user.referred_by
            wallet, created = Wallet.objects.get_or_create(user=referrer, defaults={'balance': Decimal('50')})
            if not created:
                wallet.balance += Decimal('50')
                wallet.save()

            # Create a wallet transaction for the referrer
            WalletTransaction.objects.create(
                wallet=wallet,
                order=order,
                amount=Decimal('50'),
                type='CREDIT'
            )

        return order

@csrf_exempt
def razorpay_callback(request):
    if request.method == "POST":
        try:
            # Get payment details
            payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')
            print('1')

            # Verify signature
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            try:
                client.utility.verify_payment_signature(params_dict)
                
                payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
                payment.status = 'SUCCESS'
                payment.transaction_id = payment_id
                payment.save()

                order = Order.objects.get(payment=payment)
                order.status = 'CONFIRMED'
                order.save()

                # Clear cart
                Cart.objects.filter(user=request.user).delete()

                messages.success(request, 'Payment successful! Your order has been placed.')
                return redirect('order_success') 

            except Exception as e:
                messages.error(request, 'Payment verification failed.')
                return redirect('payment_failed')

        except Exception as e:
            messages.error(request, 'An error occurred. Please contact support.')
            return redirect('payment_failed')

    return JsonResponse({'error': 'Invalid request'}, status=400)

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
            # First check if coupon exists and is valid
            coupon = Coupon.objects.get(
                code=coupon_code, 
                is_active=True, 
                expire_date__gt=timezone.now()
            )

            # Check if user has already used this coupon
            existing_usage = CouponUsage.objects.filter(
                user=request.user, 
                coupon=coupon
            ).first()

            if existing_usage and existing_usage.limit >= coupon.limit:
                return JsonResponse({
                    'success': False, 
                    'message': 'Coupon usage limit reached.'
                })

            # Calculate discount
            if coupon.type == 'PERCENTAGE':
                discount = (Decimal(coupon.discount_value) / Decimal(100)) * subtotal
            else: 
                discount = Decimal(coupon.discount_value)

            # Ensure discount doesn't exceed subtotal
            if discount > subtotal:
                discount = subtotal

            total_amount = subtotal + shipping_charge - discount

            # Store coupon info in session for later use during checkout
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

def add_money(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        amount = int(data['amount']) * 100 

        # Store the amount in session
        request.session['amount'] = amount

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        payment_order = client.order.create({'amount': amount, 'currency': 'INR', 'payment_capture': '1'})

        return JsonResponse({
            'id': payment_order['id'],
            'amount': payment_order['amount'],
            'currency': payment_order['currency']
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def payment_callback(request):
    if request.method == 'POST':
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_signature = request.POST.get('razorpay_signature')

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })

            wallet, created = Wallet.objects.get_or_create(user=request.user, defaults={'balance': Decimal('0.00')})

            amount = request.session.get('amount')
            if amount is None:
                return JsonResponse({'status': 'failed', 'message': 'Amount not found in session.'})

            amount_decimal = Decimal(amount) / Decimal('100') 

            wallet.balance += amount_decimal 
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount_decimal,
                type='CREDIT'
            )
            messages.success(request,'successfully wallet money has been added')
            return redirect('profile')
        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'status': 'failed', 'message': str(e)})

    return JsonResponse({'status': 'invalid request'})

def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get('email')

        # Check if user exists with the given email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No account found with this email.")
            return render(request, "forgot_password.html")

        # Generate OTP
        otp = generate_otp()
        otp_expiry_time = timezone.now() + timedelta(minutes=5)
        print(otp)

        # Send OTP email
        send_mail(
            'Your OTP for Password Reset',
            f'Your OTP is {otp}. It will expire in 5 minutes.',
            'fresh2home@example.com',  # Replace with your sender email
            [email],
            fail_silently=False,
        )

        # Create or update OTP record
        OTPVerification.objects.create(
            user=user,
            otp=otp,
            email_or_phone=email,
            expires_at=otp_expiry_time
        )
        request.session['reset_username'] = user.username
        print(user.username)

        request.session['next_page'] = 'password' 

        return redirect("verify_otp")  # Redirect to OTP verification page

    return render(request, "forgot_password.html")
# def forgot_password(request):
#     if request.method == "POST":
#         email = request.POST.get('email')
#         # Generate OTP
#         otp = generate_otp()
#         otp_expiry_time = timezone.now() + timedelta(minutes=5)
#         print(otp)
#         # Send OTP email
#         send_mail(
#             'Your OTP for Email Verification To Reset Password',
#             f'Your OTP is {otp}. It will expire in 5 minutes.',
#             'fresh2home@example.com',  # Replace with your email
#             [email],
#             fail_silently=False,
#         )
#         messages.success(request, 'Account created successfully! Please check your email for the OTP.')
#         return redirect('verify_otp1')
        
#     return render(request, "forgot_password.html")

# def otp(request):
#     return render(request,'otp.html')
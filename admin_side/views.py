from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login , logout
from django.contrib import messages
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from user_side.models import Products , Category ,ProductImage , User , Review,Banner,Order,OrderItem,ProductVariant,Coupon,Store,Complaint,WalletTransaction,Wallet,Address,Transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.utils import timezone
from decimal import Decimal
from django.core.paginator import Paginator,InvalidPage
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from openpyxl import Workbook
from io import BytesIO
from django.core.mail import send_mail


@never_cache
def adminlogin(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('products') 
        else:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('signin') 

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_superuser:
                login(request, user)
                return redirect('products')
            else:
                return redirect('homepage')  
        else:
            messages.error(request, 'Invalid username or password.')
            return redirect('adminlogin')

    return render(request, 'admin_login.html')

from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

import pandas as pd
from io import BytesIO
from django.db.models.functions import TruncDate
@login_required(login_url='adminlogin')
def sales_report(request):
    # Get filter parameters
    filter_type = request.GET.get('filter', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Start with all orders
    orders = Order.objects.all()

    # Apply filters based on request parameters
    if filter_type == 'daily':
        today = timezone.now().date()
        orders = orders.filter(order_date=today)
    elif filter_type == 'weekly':
        week_ago = timezone.now().date() - timedelta(days=7)
        orders = orders.filter(order_date__gte=week_ago)
    elif filter_type == 'monthly':
        month_ago = timezone.now().date() - timedelta(days=30)
        orders = orders.filter(order_date__gte=month_ago)
    elif filter_type == 'yearly':
        orders = orders.filter(order_date__year=timezone.now().year)
    elif filter_type == 'custom' and start_date and end_date:
        orders = orders.filter(order_date__range=[start_date, end_date])

    # Prepare basic report data
    report = {
        'total_orders': orders.count(),
        'total_sales': orders.aggregate(total=Sum('net_amount'))['total'] or 0,
        'total_discount': orders.aggregate(total=Sum('discount'))['total'] or 0,
        'coupon_orders': orders.exclude(coupon__isnull=True).count(),
    }

    # Calculate top 10 products based on sales
    top_products = (
        OrderItem.objects.filter(order__in=orders)
        .values('product__name')
        .annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('total_amount')
        )
        .order_by('-total_sales')[:10]
    )

    # Calculate top 10 categories based on aggregated product sales
    top_categories = (
        OrderItem.objects.filter(order__in=orders)
        .values('product__category__name')
        .annotate(total_sales=Sum('total_amount'))
        .order_by('-total_sales')[:10]
    )

    report['top_products'] = list(top_products)
    report['top_categories'] = list(top_categories)

    # Build chart data: group orders by date and sum net_amount
    chart_data_qs = (
        orders.annotate(date=TruncDate('order_date'))
        .values('date')
        .annotate(daily_sales=Sum('net_amount'))
        .order_by('date')
    )

    chart_data = [
        {
            'date': item['date'].strftime("%Y-%m-%d") if item['date'] else '',
            'daily_sales': float(item['daily_sales']) if item['daily_sales'] else 0,
        }
        for item in chart_data_qs
    ]
    report['chart_data'] = chart_data

    # Handle download requests for PDF or Excel export
    if request.GET.get('download') == 'true':
        format = request.GET.get('format', 'pdf')
        if format == 'pdf':
            return generate_pdf(request, orders, report)
        elif format == 'excel':
            return generate_excel(orders, report)

    # If the request is an AJAX request, return JSON data
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse(report)

    # Otherwise, render the HTML template with the report data
    return render(request, 'sales_report.html', {
        'report': report,
        'filter_type': filter_type,
        'start_date': start_date,
        'end_date': end_date
    })
@login_required(login_url='adminlogin')
def generate_excel(orders, report):
    data = {
        'Order ID': [order.id for order in orders],
        'Date': [order.order_date.strftime("%Y-%m-%d") for order in orders],
        'Customer': [order.user.username for order in orders],
        'Amount': [order.net_amount for order in orders],
        'Discount': [order.discount for order in orders],
        'Coupon': [order.coupon_code or 'N/A' for order in orders],
        'Status': [order.status for order in orders],
    }
    
    df = pd.DataFrame(data)

    # Create a BytesIO buffer for the Excel file
    buffer = BytesIO()
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sales Report')
        
        summary_df = pd.DataFrame({
            'Summary': ['Total Orders', 'Total Sales', 'Total Discount', 'Coupon Orders'],
            'Value': [report['total_orders'], report['total_sales'], report['total_discount'], report['coupon_orders']]
        })
        summary_df.to_excel(writer, index=False, sheet_name='Summary')

    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="sales_report_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    return response

@login_required(login_url='adminlogin')
def generate_pdf(request, orders, report):
    # Option 1: Using reportlab directly
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    # PDF Content
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, "Fresh 2 Home - Sales Report")
    
    p.setFont("Helvetica", 12)
    p.drawString(100, 770, f"Total Orders: {report['total_orders']}")
    p.drawString(100, 750, f"Total Sales: ₹{report['total_sales']:.2f}")
    p.drawString(100, 730, f"Total Discount: ₹{report['total_discount']:.2f}")
    p.drawString(100, 710, f"Coupon Orders: {report['coupon_orders']}")
    
    # Add order table
    y_position = 660
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y_position, "Order ID")
    p.drawString(120, y_position, "Date")
    p.drawString(220, y_position, "Customer")
    p.drawString(320, y_position, "Amount")
    p.drawString(400, y_position, "Status")
    
    p.setFont("Helvetica", 10)
    y_position -= 20
    
    for order in orders[:20]:  # Limit to 20 orders per page
        p.drawString(50, y_position, str(order.id))
        p.drawString(120, y_position, order.order_date.strftime("%Y-%m-%d"))
        p.drawString(220, y_position, order.user.username)
        p.drawString(320, y_position, f"₹{order.net_amount:.2f}")
        p.drawString(400, y_position, order.status)
        y_position -= 20
        
        # Start a new page if needed
        if y_position < 50:
            p.showPage()
            p.setFont("Helvetica-Bold", 12)
            y_position = 800
            p.drawString(50, y_position, "Order ID")
            p.drawString(120, y_position, "Date")
            p.drawString(220, y_position, "Customer")
            p.drawString(320, y_position, "Amount")
            p.drawString(400, y_position, "Status")
            p.setFont("Helvetica", 10)
            y_position -= 20

    p.showPage()
    p.save()
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="sales_report_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response

@login_required(login_url='adminlogin')
def store(request):
    if request.method == "POST":
        store_id = request.POST.get('store_id')  # Check if it's an edit operation
        store_name = request.POST.get('store')
        pincode = request.POST.get('pincode')
        status = request.POST.get('status') == "True"  # Convert select input to Boolean
        
        if store_name and pincode:
            if store_id:  # Editing an existing store
                store_instance = get_object_or_404(Store, id=store_id)
                store_instance.store = store_name
                store_instance.pincode = pincode
                store_instance.is_active = status
                store_instance.save()
                messages.success(request, "Store updated successfully!")
            else:  # Adding a new store
                Store.objects.create(store=store_name, pincode=pincode, is_active=status)
                messages.success(request, "Store added successfully!")
        else:
            messages.error(request, "Please fill in all required fields.")
        
        return redirect('store')  # Redirect to store list

    store_list = Store.objects.all().order_by('-id')
    paginator = Paginator(store_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'stores.html', {'data': page_obj})

@never_cache
def customers(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            customers = User.objects.filter(is_superuser=False)
            paginator = Paginator(customers, 10)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            return render(request, 'customers.html', {'data': page_obj}) 
        else:
            return redirect('homepage')
    return redirect('userlogin')

@never_cache
def delete_customer(request, customer_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    customer = get_object_or_404(User, id=customer_id)
    
    try:
        Address.objects.filter(user=customer).delete()
        customer.delete() 
        messages.success(request, "Customer and its related data were successfully deleted.")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
    
    return redirect('customers')



def user_active(request, user_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user.is_active = not user.is_active
        user.save()
        return JsonResponse({'status': 'success', 'is_active': user.is_active})
    return JsonResponse({'status': 'error'}, status=400)


@never_cache
@login_required
def add_variant(request, product_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    product = get_object_or_404(Products, id=product_id)

    if request.method == 'POST':
        try:
            weight = request.POST.get('weight')
            price = request.POST.get('price')
            available_quantity = request.POST.get('available_quantity')

            if not weight or not price or not available_quantity:
                messages.error(request, 'Please fill in all fields.')
                return redirect('products')

            ProductVariant.objects.create(
                product=product,
                weight=weight,
                price=price,
                available_quantity=available_quantity
            )

            messages.success(request, 'Variant created successfully.')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return redirect('products')

@login_required
def product_list(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')

    products = Products.objects.all().prefetch_related('images')
    categories = Category.objects.all()

    category_id = request.GET.get('category')
    sort_by = request.GET.get('sort')
    status = request.GET.get('status')

    # Apply filters
    if category_id:
        try:
            category_id = int(category_id)
            products = products.filter(category_id=category_id)
        except ValueError:
            messages.error(request, 'Invalid category ID.')
            return redirect('products')

    if status:
        if status == 'in_stock':
            products = products.filter(available_quantity__gt=0)
        elif status == 'out_of_stock':
            products = products.filter(available_quantity=0)
        else:
            messages.error(request, 'Invalid status.')
            return redirect('products')

    # Apply sorting
    if sort_by:
        sort_options = {
            'price_low': 'price',
            'price_high': '-price',
            'name_asc': 'name',
            'name_desc': '-name',
            'newest': '-created_at',
            'oldest': 'created_at'
        }
        if sort_by in sort_options:
            products = products.order_by(sort_options[sort_by])
        else:
            messages.error(request, 'Invalid sort option.')
            return redirect('products')

    # Pagination
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except (ValueError, InvalidPage):
        page_obj = paginator.get_page(1)

    weight_choices = ProductVariant.WEIGHT_CHOICES

    context = {
        'data': page_obj,
        'categories': categories,
        'selected_category': category_id,
        'selected_sort': sort_by,
        'selected_status': status,
        'weight_choices': weight_choices
    }

    return render(request, 'products.html', context)



@never_cache
@login_required
def add_product(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    if request.method == 'POST':
        try:
            available_quantity = request.POST.get('available_quantity', '0').strip()
            price = request.POST.get('price', '0').strip()
            discount = request.POST.get('discount')

            available_quantity = int(available_quantity) if available_quantity.isdigit() else 0
            try:
                price = Decimal(price)
            except InvalidOperation:
                price = Decimal(0)

            variants = request.POST.getlist('variant')
            variant_prices = [Decimal(p) if p.replace('.', '', 1).isdigit() else Decimal(0) for p in request.POST.getlist('variant_price')]
            variant_quantities = [int(q) if q.isdigit() else 0 for q in request.POST.getlist('variant_quantity')]

            # Create Product
            product = Products.objects.create(
                name=request.POST.get('product_name'),
                category=Category.objects.get(id=request.POST.get('category')),
                price=price,
                available_quantity=available_quantity,
                discount = discount,
                description=request.POST.get('description')
            )

            # Handle Image Uploads
            images = request.FILES.getlist('image')
            for image in images:
                ProductImage.objects.create(product=product, image_url=image)

            messages.success(request, 'Product and images added successfully')
            return redirect('products')

        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('products')

    return redirect("add_products")

def delete_product(request, product_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    product = get_object_or_404(Products, id=product_id)
    
    try:
        product.delete() 
        messages.success(request, "Product and its related data were successfully deleted.")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
    
    return redirect('products') 

@never_cache
@login_required
def edit_product(request, product_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    product = get_object_or_404(Products, id=product_id)

    if request.method == "POST":
        try:
            product_name = request.POST.get("product_name")
            category_id = request.POST.get("category")
            price = request.POST.get("price")
            available_quantity = request.POST.get("available_quantity")
            description = request.POST.get("description")
            discount = request.POST.get("discount")
            images = request.FILES.getlist("image")

            # Get existing variant data
            variant_ids = request.POST.getlist('variant_ids[]')
            variant_weights = request.POST.getlist('variant_weights[]')
            variant_prices = request.POST.getlist('variant_prices[]')
            variant_quantities = request.POST.getlist('variant_quantities[]')

            new_variant_weights = request.POST.getlist('new_variant_weights[]')
            new_variant_prices = request.POST.getlist('new_variant_prices[]')
            new_variant_quantities = request.POST.getlist('new_variant_quantities[]')

            if int(available_quantity) < 0:
                messages.error(request, 'Invalid available stock')
                return redirect('products')

            product.name = product_name
            product.category = get_object_or_404(Category, id=category_id)
            product.price = price
            product.available_quantity = available_quantity
            product.description = description
            if discount:
                product.discount = Decimal(discount)
            else:
                product.discount = None
            product.save()

            if images:
                for img in images:
                    ProductImage.objects.create(product=product, image_url=img)

            for var_id, weight, price, quantity in zip(variant_ids, variant_weights, variant_prices, variant_quantities):
                if var_id:
                    variant = ProductVariant.objects.get(id=var_id)
                    variant.weight = weight
                    variant.price = price
                    variant.available_quantity = quantity
                    variant.save()

            variants_to_delete = request.POST.getlist('delete_variants[]')
            if variants_to_delete:
                ProductVariant.objects.filter(id__in=variants_to_delete).delete()

            messages.success(request, "Product updated successfully!")
            return redirect("products")

        except Exception as e:
            messages.error(request, f"Error updating product: {str(e)}")
            return redirect("products")

    categories = Category.objects.all()
    weight_choices = ProductVariant.WEIGHT_CHOICES
    context = {
        "product": product,
        "categories": categories,
        "weight_choices": weight_choices
    }
    return render(request, "products.html", context)


def delete_image(request, image_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    image = get_object_or_404(ProductImage, id=image_id)
    product_id = image.product.id
    image.delete()

    messages.success(request, "Image deleted successfully!")
    return redirect("edit_product", product_id=product_id)

@never_cache
@login_required
def admin_orders(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    orders = (
        Order.objects
        .select_related("user", "address")
        .prefetch_related("items__product", "payment")
        .all()
    )

    # Pagination
    paginator = Paginator(orders, 10)  # Show 10 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'data': page_obj  # Contains paginated order data
    }

    return render(request, 'adminorders.html', context)

@never_cache
@login_required
def update_order_status(request, order_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    if request.method == 'POST':
        try:
            order = Order.objects.get(id=order_id)
            new_status = request.POST.get('status')
            
            # status
            if new_status in dict(Order.STATUS_CHOICES):
                if new_status == 'DELIVERED' and order.status != 'DELIVERED':
                    order.delivery_date = timezone.now().date()
                
                if new_status == 'CANCELLED' and order.status != 'CANCELLED':
                    if order.payment and order.payment.status == 'SUCCESS':
                        pass

                order.status = new_status
                order.save()
                messages.success(request, f'Order status updated to {new_status}')
            else:
                messages.error(request, 'Invalid status value')
                
        except Order.DoesNotExist:
            messages.error(request, 'Order not found')
        
        return redirect('orders')

    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required
def delete_order(request, order_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    order = get_object_or_404(Order, id=order_id)
    order.delete()
    messages.success(request, "Order deleted successfully!")
    return redirect('orders')

def coupon(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    coupons = Coupon.objects.all()
    paginator = Paginator(coupons, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request , 'coupon.html',{'data':page_obj})

def save_coupon(request, coupon_id=None):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    if request.method == 'POST':
        code = request.POST.get('code')
        discount_type = request.POST.get('type')
        discount_value = request.POST.get('discount_value')
        description = request.POST.get('description')
        limit = request.POST.get('limit')
        expire_date = request.POST.get('expire_date')
        is_active = request.POST.get('is_active') == 'on'

        if coupon_id:
            coupon = get_object_or_404(Coupon, id=coupon_id)
            coupon.code = code
            coupon.type = discount_type
            coupon.discount_value = discount_value
            coupon.description = description
            coupon.limit = limit
            coupon.expire_date = expire_date
            coupon.is_active = is_active
            coupon.save()
            messages.success(request, 'Coupon updated successfully!')
        else: 
            Coupon.objects.create(
                code=code,
                type=discount_type,
                discount_value=discount_value,
                description=description,
                limit=limit,
                expire_date=expire_date,
                is_active=is_active
            )
            messages.success(request, 'Coupon added successfully!')

        return redirect('coupon')
    
    coupons = Coupon.objects.all()
    paginator = Paginator(coupons, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'coupon.html', {'data': page_obj})

def edit_coupon(request, coupon_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupons = Coupon.objects.all()
    paginator = Paginator(coupons, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'coupon.html', {'data': page_obj, 'edit_coupon': coupon, 'edit_mode': True})

def toggle_coupon_status(request, coupon_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.is_active = not coupon.is_active  # Toggle the status
    coupon.save()
    messages.success(request, f'Coupon status updated to {"Active" if coupon.is_active else "Not Active"}!')
    return redirect('coupon')

def delete_coupon(request, coupon_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.delete()
    messages.success(request, 'Coupon deleted successfully!')
    return redirect('coupon')

def banner(request):
    if request.user.is_superuser:
        banners = Banner.objects.all()
        paginator = Paginator(banners, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        return render(request, 'banner.html', {'data': page_obj,})
    else:
        return redirect('signin')

@never_cache
@login_required
def add_banner(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')

    if request.method == 'POST':
        banner_name = request.POST.get('name')
        banner_code = request.POST.get('code')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        status = request.POST.get('status')
        image_file = request.FILES.get('image')

        if not (banner_name and banner_code and start_date and end_date and status and image_file):
            messages.error(request, 'All fields are required.')
            return redirect('add_banner')

        try:
            Banner.objects.create(
                name=banner_name,
                code=banner_code,
                start_date=start_date,
                end_date=end_date,
                status=status,
                image=image_file
            )

            messages.success(request, 'Banner added successfully!')
            return redirect('banner')

        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect('add_banner')

    return render(request, 'banner.html')

@login_required
def edit_banner(request, banner_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    banner = get_object_or_404(Banner, id=banner_id)

    if request.method == "POST":
        banner.name = request.POST.get("name", banner.name)
        banner.code = request.POST.get("code", banner.code)
        banner.start_date = request.POST.get("start_date", banner.start_date)
        banner.end_date = request.POST.get("end_date", banner.end_date)
        banner.status = request.POST.get("status", banner.status)

        if "image" in request.FILES:
            banner.image = request.FILES["image"]

        banner.save()
        messages.success(request, "Banner updated successfully!")
        return redirect("banner")  # Redirect to banners page

    # If GET request, render the edit form
    return render(request, "banner.html", {"banner": banner})

def delete_banner(request, id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    banner = get_object_or_404(Banner, id=id)
    banner.delete()
    return redirect('banner')


@login_required
def category(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    
    category = Category.objects.all()
    paginator = Paginator(category, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request , 'category.html',{'data': page_obj,})
    
def category_active(request, category_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    if request.method == 'POST':
        category = get_object_or_404(Category, id=category_id)
        category.is_active = not category.is_active
        category.save()
        return JsonResponse({'status': 'success', 'is_active': category.is_active})
    return JsonResponse({'status': 'error'}, status=400)
    
def add_category(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    if request.method == 'POST':
        name = request.POST.get('categoryname')
        description = request.POST.get('description')

        Category.objects.create(name=name , description=description)
        return redirect('category')
    return redirect('category')

@login_required
def add_category(request):
    if not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('homepage') 

    if request.method == 'POST':
        name = request.POST.get('categoryname')
        description = request.POST.get('description')

        Category.objects.create(name=name, description=description)
        messages.success(request, 'Category added successfully!')
        return redirect('category')

    return redirect('category') 

def delete_category(request, category_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    category = get_object_or_404(Category, id=category_id)

    try:
        category.delete()
        messages.success(request, "Category and its related data were successfully deleted.")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
    return redirect('category') 

@login_required
def edit_category(request, category_id):
    if not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('homepage')

    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        discount = request.POST.get("discount")

        category.name = name
        category.description = description
        category.discount = float(discount) if discount else None
        category.save()

        messages.success(request, 'Category updated successfully!')
        return redirect('category')

    return redirect('category')


def logout_admin(request):
    logout(request)
    return redirect('adminlogin') 

@login_required
def complaints(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    complaints_list = Complaint.objects.select_related('order_item__order', 'order_item__product')
    paginator = Paginator(complaints_list, 10)  # Show 10 complaints per page
    page_number = request.GET.get('page')
    complaints = paginator.get_page(page_number)
    
    context = {
        'data': complaints
    }
    return render(request, 'complaints.html', context)

@login_required
def update_complaint_status(request, complaint_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    complaint = get_object_or_404(Complaint, id=complaint_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        complaint.status = new_status
        complaint.save()

        complaint.order_item.order.status = new_status
        complaint.order_item.order.save()
        user = complaint.order_item.order.user
        order_item = complaint.order_item
        # If the complaint is resolved, refund only the specific product's price
        if new_status == 'RESOLVED':
            
            product_price = (order_item.variant.price) * order_item.quantity 

            wallet, created = Wallet.objects.get_or_create(user=user, defaults={'balance': Decimal('0.00')})

            wallet.balance += product_price
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                order=order_item.order,
                amount=product_price,
                type='CREDIT'
            )
            send_mail(
                subject="Complaint Resolved - Refund Issued",
                message=(
                    f"Dear {user.username},\n\n"
                    f"Your complaint regarding the product '{order_item.product.name}' has been resolved. "
                    f"A refund of ₹{product_price} has been credited to your wallet.\n\n"
                    f"Thank you for your patience.\n\n"
                    f"Best Regards,\nFresh 2 Home Support Team"
                ),
                from_email='support@fresh2home.com',
                recipient_list=[user.email],
                fail_silently=False,
            )

            messages.success(request, f'₹{product_price} has been refunded to the wallet for the complained product.')
        elif new_status == 'REJECTED':
            # Send rejection email
            send_mail(
                subject="Complaint Rejected",
                message=(
                    f"Dear {user.username},\n\n"
                    f"Your complaint regarding the product '{order_item.product.name}' has been reviewed, "
                    f"but unfortunately, it has been rejected. No refund will be provided for this complaint.\n\n"
                    f"If you have any further concerns, please contact our support team.\n\n"
                    f"Best Regards,\nFresh 2 Home Support Team"
                ),
                from_email='support@fresh2home.com',
                recipient_list=[user.email],
                fail_silently=False,
            )

            messages.warning(request, f"Complaint rejected. No refund issued.")

    return redirect('complaints_list')

@login_required
def delete_complaint(request, complaint_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    complaint = get_object_or_404(Complaint, id=complaint_id)
    if request.method == 'POST':
        complaint.delete()
        messages.success(request, 'Complaint deleted successfully.')
    return redirect('complaints')

def resolve_complaint(request, complaint_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    complaint = get_object_or_404(Complaint, id=complaint_id)
    
    # Ensure the complaint is not already resolved
    if complaint.status == 'RESOLVED':
        messages.warning(request, "This complaint has already been resolved.")
        return redirect('complaints_list')
    
    user_wallet = Wallet.objects.get(user=complaint.user)
    
    refund_amount = Decimal(complaint.order_item.variant.price) * Decimal(complaint.order_item.quantity)

    user_wallet.balance += refund_amount
    user_wallet.save()

    WalletTransaction.objects.create(
        wallet=user_wallet,
        order=complaint.order_item.order,
        amount=refund_amount,
        type='CREDIT'
    )

    complaint.status = 'RESOLVED'
    complaint.save()

    messages.success(request, f"₹{refund_amount} refunded to {user_wallet.user.username}'s wallet for the complained product.")
    return redirect('complaints_list')

def wallet(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    wallet = Wallet.objects.all()
    return render(request,'wallet.html',{ 'wallets': wallet })

def offers(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    products = Products.objects.filter(discount__gt=0)  # Get products with discounts
    categories = Category.objects.filter(discount__gt=0)  # Get categories with discounts

    context = {
        'products': products,  # Pass products to template
        'categories': categories  # Pass categories to template
    }

    return render(request, 'offers.html', context)


def transactions(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('homepage')
    transaction = Transaction.objects.all()
    return render(request,'transaction.html',{ 'transaction': transaction })

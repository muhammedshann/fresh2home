from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import random ,string
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.db.models.signals import pre_save
from django.dispatch import receiver
import uuid
from django.db.models.signals import post_save


class User(AbstractUser):
    first_name = None
    last_name = None
    
    profile = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    phone_no = models.CharField(max_length=15)
    is_admin = models.BooleanField(default=False)
    is_verify = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    referral_id = models.CharField(max_length=10, unique=True, null=True, blank=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')

    class Meta:
        db_table = 'users'
        ordering = ['created_at']

@receiver(pre_save, sender=User)
def generate_referral_id(sender, instance, **kwargs):
    if not instance.referral_id:  # Generate only if it's empty
        instance.referral_id = instance.username[:3].upper() + uuid.uuid4().hex[:6].upper()

class Address(models.Model):
    ADDRESS_TYPES = [
        ('HOME', 'Home'),
        ('WORK', 'Work'),
        ('OTHER', 'Other')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    pin_code = models.CharField(max_length=10)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES)
    land_mark = models.CharField(max_length=255, blank=True, null=True)
    mobile_number = models.CharField(max_length=15)
    alternate_number = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'addresses'

class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = 'categories'
        ordering = ['created_at']

class Products(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    available_quantity = models.IntegerField()
    description = models.TextField()
    discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)  # Changed default to True

    class Meta:
        db_table = 'products'
        ordering = ['-created_at'] 

    def soft_delete(self):
        self.is_active = False
        self.save()

    def discounted_price(self):
        """Returns the final price after applying the discount percentage"""
        if self.discount and self.discount > 0:
            discount_amount = (self.discount / 100) * self.price
            return self.price - discount_amount
        return self.price


    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='images')
    image_url = models.ImageField(upload_to='product_images/')

    class Meta:
        db_table = 'product_images'

class ProductVariant(models.Model):
    WEIGHT_CHOICES = [
        ('250', '250 Grams'),
        ('500', '500 Grams'),
        ('750', '750 Grams'),
        ('1000', '1 Kilogram')
    ]
    
    product = models.ForeignKey('Products', on_delete=models.CASCADE, related_name='variants')
    weight = models.CharField(max_length=10, choices=WEIGHT_CHOICES)  # Changed IntegerField to CharField
    price = models.DecimalField(max_digits=10, decimal_places=2)
    available_quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_variants'
        unique_together = ['product', 'weight']
    
    def discounted_price(self):
        """Applies the product's discount percentage to this variant"""
        if self.product.discount and self.product.discount > 0:
            discount_amount = (self.product.discount / 100) * self.price
            return max(self.price - discount_amount, 0)  # Ensure price never goes negative
        return self.price


    
    def __str__(self):
        return f"{self.product.name} - {self.get_weight_display()}"
    
class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    products = models.ManyToManyField(Products, related_name="wishlisted_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wishlists'

class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Products, on_delete=models.CASCADE)

    class Meta:
        db_table = 'wishlist_items'

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'carts'

class CartItem(models.Model):
    cart = models.ForeignKey('Cart', related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey('Products', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    price_at_time = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)  # Store price when added to cart

    class Meta:
        db_table = 'cart_items'
    
    def save(self, *args, **kwargs):
        """Ensure the discounted price is stored in the cart"""
        if not self.price_at_time:
            if self.variant:
                self.price_at_time = self.variant.discounted_price()  # Use the variant's discounted price
            else:
                self.price_at_time = self.product.discounted_price()  # Use the product's discounted price
        super().save(*args, **kwargs)

    @property
    def total_price(self):
        """Calculate total price for this cart item"""
        return self.price_at_time * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled')
    ]
    
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, null=True, related_name='orders')
    address = models.ForeignKey('Address', on_delete=models.PROTECT)
    order_date = models.DateField(auto_now=True)
    delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    shipping_chrg = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancellation_reason = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'orders'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Products', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    variant = models.ForeignKey('ProductVariant', on_delete=models.PROTECT, null=True, blank=True)
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)  # Add this field

    def save(self, *args, **kwargs):
        """Ensure the correct total amount is stored in the database"""
        if not self.price_at_order:
            if self.variant:
                self.price_at_order = self.variant.discounted_price()
            else:
                self.price_at_order = self.product.discounted_price()
        
        self.total_amount = self.price_at_order * self.quantity  # Store total price
        super().save(*args, **kwargs)


class Review(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField()
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reviews'

class ContactUs(models.Model):
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved')
    ]
    
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    class Meta:
        db_table = 'contact_us'

class Banner(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive')
    ]
    
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='banners/')
    code = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'banners'

class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('PERCENTAGE', 'Percentage'),
        ('FLAT', 'Flat')
    ]
    
    code = models.CharField(max_length=50, unique=True)
    type = models.CharField(max_length=10, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    limit = models.PositiveIntegerField()
    expire_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'coupons'
        ordering = ['expire_date']

class CouponUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    limit = models.PositiveIntegerField(default=1)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coupon_usage'
        unique_together = ('user', 'coupon')

class Offer(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    offer = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        db_table = 'offers'

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('ORDER', 'Order'),
        ('PROMOTION', 'Promotion'),
        ('SYSTEM', 'System')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notifications'

class Payment(models.Model):
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending')
    ]
    
    PAYMENT_METHODS = [
        ('CREDIT_CARD', 'Credit Card'),
        ('DEBIT_CARD', 'Debit Card'),
        ('WALLET', 'Wallet'),
        ('COD', 'Cash on Delivery') 
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    wallet = models.ForeignKey('Wallet', on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    date = models.DateTimeField()
    razorpay_order_id = models.CharField(max_length=255, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=255, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'payments'

class Transaction(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField()

    class Meta:
        db_table = 'transactions'

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wallets'

# Signal to create a wallet when a user is created
@receiver(post_save, sender=User)
def create_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)

class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit')
    ]
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wallet_transactions'

class OTPVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6) 
    email_or_phone = models.EmailField()  
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified = models.BooleanField(default=False) 

    def is_expired(self):
        return self.expires_at < timezone.now()

    def __str__(self):
        return f"OTP for {self.email_or_phone}"
    
class Store(models.Model):
    store = models.CharField(max_length=20)
    pincode = models.CharField(max_length=7)
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = 'stores'

class Complaint(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('REJECTED', 'Rejected'),
    ]

    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name="complaints")
    description = models.TextField()
    image = models.ImageField(upload_to='complaints/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "complaints"

    def __str__(self):
        return f"Complaint for {self.order_item.product.name} - {self.get_status_display()}"

from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
 


# app_name ='admin'

urlpatterns = [
    path('', views.adminlogin, name='adminlogin'),
    path('sales-report/', views.sales_report, name='sales_report'),
    # path('download-report/', views.download_report, name='download_report'),
    path('store/', views.store, name='store'),
    path('customers/',views.customers,name='customers'),
    path('delete_customer/<int:customer_id>/', views.delete_customer, name='delete_customer'),
    path('orders/', views.admin_orders, name='orders'),
    path('orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('admin/orders/delete/<int:order_id>/', views.delete_order, name='delete_order'),
    path('reviews/',views.reviews,name='reviews'),
    path('offers/',views.offers,name='offers'),
    path('contactus/',views.contactus,name='contactus'),
    path('coupons/', views.coupon, name='coupon'),
    path('save-coupon/', views.save_coupon, name='save_coupon'),
    path('save-coupon/<int:coupon_id>/', views.save_coupon, name='save_coupon'),
    path('edit-coupon/<int:coupon_id>/', views.edit_coupon, name='edit_coupon'),
    path('delete-coupon/<int:coupon_id>/', views.delete_coupon, name='delete_coupon'),
    path('toggle-coupon-status/<int:coupon_id>/', views.toggle_coupon_status, name='toggle_coupon_status'),
    path('banner/',views.banner,name='banner'),
    path('add-banner/', views.add_banner, name='add_banner'),
    path('banner/edit/<int:banner_id>/', views.edit_banner, name='edit_banner'),
    path('delete_banner/<int:id>/', views.delete_banner, name='delete_banner'),
    path('category/',views.category,name='category'),
    path('notification/',views.notification,name='notification'),
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('products/', views.product_list, name='products'),
    path('add-product/', views.add_product, name='add_product'),
    path('add-category/', views.add_category, name='add_category'),
    path('add_variant/<int:product_id>/', views.add_variant, name='add_variant'),
    path('category-status/<int:category_id>/', views.category_active, name='category_active'),
    path('toggle-user-block/<int:user_id>/', views.user_active, name='user_active'),
    path('admin/delete-category/<int:category_id>/', views.delete_category , name='delete_category'),
    path('categories/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path("edit_product/<int:product_id>/", views.edit_product, name="edit_product"),
    path("delete_image/<int:image_id>/", views.delete_image, name="delete_image"),
    path('admin/logout/', views.logout_admin, name='logout_admin'),
    path('complaints/', views.complaints, name='complaints_list'),
    path('complaints/update/<int:complaint_id>/', views.update_complaint_status, name='update_complaint_status'),
    path('complaints/delete/<int:complaint_id>/', views.delete_complaint, name='delete_complaint'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


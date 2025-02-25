# # admin_side/forms.py
# from django import forms
# from user_side.models import Product, ProductImage  # Note: Changed from Products to Product

# class ProductForm(forms.ModelForm):
#     images = forms.FileField(
#         widget=forms.ClearableFileInput(attrs={'multiple': True, 'class': 'form-control'}),
#         required=True
#     )
    
#     class Meta:
#         model = Product  # Note: Changed from Products to Product
#         fields = ['name', 'category', 'price', 'available_quantity', 'description']
#         widgets = {
#             'name': forms.TextInput(attrs={'class': 'form-control'}),
#             'category': forms.Select(attrs={'class': 'form-control'}),
#             'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
#             'available_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
#             'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
#         }
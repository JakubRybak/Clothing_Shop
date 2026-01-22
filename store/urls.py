from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('accounts/register/', views.register, name='register'),
    path('accounts/', include('django.contrib.auth.urls')), # Built-in login/logout
    path('category/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('add-to-cart/<int:variant_id>/', views.add_to_cart, name='add_to_cart'),
    path('add-to-cart-form/', views.add_to_cart_form, name='add_to_cart_form'),
    path('clear-cart/', views.clear_cart, name='clear_cart'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('visual-search/', views.visual_search, name='visual_search'),
    path('<slug:slug>/', views.product_detail, name='product_detail'),  
]
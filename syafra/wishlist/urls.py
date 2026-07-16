from django.urls import path

from . import views

app_name = 'wishlist'

urlpatterns = [
    path('', views.wishlist_page, name='page'),
    path('add/<int:product_id>/', views.add_to_wishlist, name='add'),
    path('remove/<int:product_id>/', views.remove_from_wishlist, name='remove'),
    path('status/<int:product_id>/', views.wishlist_status, name='status'),
    path('count/', views.wishlist_count, name='count'),
]

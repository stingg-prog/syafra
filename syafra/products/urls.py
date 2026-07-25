from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('category/<str:slug>/', views.category_detail, name='category_detail'),
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    path('pages/<slug:slug>/', views.content_page, name='content_page'),
    path('contact/', views.contact, name='contact'),
    path('track-order/', views.track_order, name='track_order'),
    path('section-preview/<int:section_id>/', views.section_preview, name='section_preview'),
    path('theme/export/', views.theme_export, name='theme_export'),
    path('theme/import/', views.theme_import, name='theme_import'),
    path('theme/reset/', views.theme_reset, name='theme_reset'),
    path('theme/backups/', views.backup_list, name='backup_list'),
    path('theme/backup/create/', views.backup_create, name='backup_create'),
    path('theme/backup/<int:backup_id>/restore/', views.backup_restore, name='backup_restore'),
    path('theme/backup/<int:backup_id>/delete/', views.backup_delete, name='backup_delete'),
    path('admin-preview/<slug:model_name>/<int:object_id>/', views.admin_preview, name='admin_preview'),
]

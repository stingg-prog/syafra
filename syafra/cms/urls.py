from django.urls import path
from . import views

app_name = 'cms'

urlpatterns = [
    path('blog/', views.BlogListView.as_view(), name='blog_list'),
    path('blog/<slug:slug>/', views.BlogDetailView.as_view(), name='blog_detail'),
    path('blog/category/<slug:slug>/', views.BlogCategoryView.as_view(), name='blog_category'),
    path('blog/author/<slug:slug>/', views.BlogAuthorView.as_view(), name='blog_author'),
    path('faq/', views.FAQView.as_view(), name='faq'),
    path('lookbook/', views.LookbookListView.as_view(), name='lookbook_list'),
    path('lookbook/<slug:slug>/', views.LookbookDetailView.as_view(), name='lookbook_detail'),
    path('<slug:slug>/', views.LegalPageView.as_view(), name='legal_page'),
]

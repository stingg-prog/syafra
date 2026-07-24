from django.db.models import Prefetch
from django.views import generic
from django.shortcuts import get_object_or_404
from . import models


class BlogListView(generic.ListView):
    model = models.BlogPost
    template_name = 'cms/blog_list.html'
    context_object_name = 'posts'
    paginate_by = 12

    def get_queryset(self):
        return models.BlogPost.objects.filter(
            is_published=True
        ).select_related('category', 'author').order_by('-published_at')


class BlogDetailView(generic.DetailView):
    model = models.BlogPost
    template_name = 'cms/blog_detail.html'
    context_object_name = 'post'

    def get_queryset(self):
        return models.BlogPost.objects.filter(is_published=True).select_related('category', 'author').prefetch_related('tags')


class BlogCategoryView(generic.ListView):
    model = models.BlogPost
    template_name = 'cms/blog_list.html'
    context_object_name = 'posts'
    paginate_by = 12

    def get_queryset(self):
        self.category = get_object_or_404(models.BlogCategory, slug=self.kwargs['slug'], is_active=True)
        return models.BlogPost.objects.filter(
            is_published=True, category=self.category
        ).select_related('category', 'author').order_by('-published_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_category'] = self.category
        return context


class BlogAuthorView(generic.ListView):
    model = models.BlogPost
    template_name = 'cms/blog_list.html'
    context_object_name = 'posts'
    paginate_by = 12

    def get_queryset(self):
        self.author = get_object_or_404(models.BlogAuthor, slug=self.kwargs['slug'], is_active=True)
        return models.BlogPost.objects.filter(
            is_published=True, author=self.author
        ).select_related('category', 'author').order_by('-published_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_author'] = self.author
        return context


class FAQView(generic.TemplateView):
    template_name = 'cms/faq.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['faq_categories'] = models.FAQCategory.objects.filter(
            is_active=True
        ).prefetch_related(
            Prefetch('items', queryset=models.FAQItem.objects.filter(is_active=True).order_by('display_order'))
        ).order_by('display_order')
        return context


class LookbookListView(generic.ListView):
    model = models.Lookbook
    template_name = 'cms/lookbook_list.html'
    context_object_name = 'lookbooks'

    def get_queryset(self):
        return models.Lookbook.objects.filter(is_published=True).order_by('display_order', '-created_at')


class LookbookDetailView(generic.DetailView):
    model = models.Lookbook
    template_name = 'cms/lookbook_detail.html'
    context_object_name = 'lookbook'

    def get_queryset(self):
        return models.Lookbook.objects.filter(is_published=True).prefetch_related(
            Prefetch('items', queryset=models.LookbookItem.objects.filter(is_active=True).order_by('display_order'))
        )


class LegalPageView(generic.DetailView):
    model = models.LegalPage
    template_name = 'cms/legal_page.html'
    context_object_name = 'page'

    def get_queryset(self):
        return models.LegalPage.objects.filter(is_active=True)

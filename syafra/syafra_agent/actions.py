import logging
import re
from decimal import Decimal, InvalidOperation
from io import BytesIO
from uuid import uuid4

import bleach
from django.contrib.admin.models import CHANGE, ADDITION, DELETION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.db.models import FileField
from django.db.models.deletion import Collector
from django.utils import timezone
from django.utils.text import slugify
from syafra.validators import validate_safe_url
from cloudinary.models import CloudinaryField

from cms.models import (
    AnnouncementBarConfig,
    Brand,
    BlogAuthor,
    BlogCategory,
    BlogTag,
    BlogPost,
    CareInstruction,
    Collection,
    CollectionProduct,
    FAQCategory,
    FAQItem,
    LegalPage,
    Lookbook,
    LookbookItem,
    PromotionalPopup,
    PromoBanner,
    ProductBadge,
    ProductLabel,
    SEOSettings,
    SizeChart,
    TestimonialExtended,
    SiteNavigation,
)
from products.models import (
    Category,
    ContentPage,
    HeroSlide,
    HomepageSection,
    FooterLink,
    ShopByCategoryItem,
    Product,
    ProductImage,
    ProductSize,
    InstagramFeedItem,
    PromotionalBannerConfig,
    Testimonial,
    TrustBarItem,
    ThemeSettings,
    WebsiteSettings,
)
from products.utils.image_normalizer import (
    NORMALIZATION_VERSION,
    compute_image_hash,
    render_product_price_callout,
)

from .models import AgentAttachment, AgentProposal, private_upload_storage
from .schemas import ACTION_FIELDS, VALUE_FIELDS

logger = logging.getLogger(__name__)

ACTION_PERMISSIONS = {
    "product_create": "products.add_product",
    "product_update": "products.change_product",
    "theme_update": "products.change_themesettings",
    "homepage_section_create": "products.add_homepagesection",
    "homepage_section_update": "products.change_homepagesection",
    "announcement_update": "cms.change_announcementbarconfig",
    "banner_create": "cms.add_promobanner",
    "banner_update": "cms.change_promobanner",
    "content_page_create": "products.add_contentpage",
    "content_page_update": "products.change_contentpage",
    "website_settings_update": "products.change_websitesettings",
    "category_create": "products.add_category",
    "category_update": "products.change_category",
    "navigation_create": "cms.add_sitenavigation",
    "navigation_update": "cms.change_sitenavigation",
    "blog_post_create": "cms.add_blogpost",
    "blog_post_update": "cms.change_blogpost",
    "faq_category_create": "cms.add_faqcategory",
    "faq_category_update": "cms.change_faqcategory",
    "faq_item_create": "cms.add_faqitem",
    "faq_item_update": "cms.change_faqitem",
    "legal_page_create": "cms.add_legalpage",
    "legal_page_update": "cms.change_legalpage",
    "popup_create": "cms.add_promotionalpopup",
    "popup_update": "cms.change_promotionalpopup",
    "hero_slide_create": "products.add_heroslide",
    "hero_slide_update": "products.change_heroslide",
    "seo_update": "cms.change_seosettings",
    "brand_create": "cms.add_brand",
    "brand_update": "cms.change_brand",
    "shop_category_create": "products.add_shopbycategoryitem",
    "shop_category_update": "products.change_shopbycategoryitem",
    "trust_item_create": "products.add_trustbaritem",
    "trust_item_update": "products.change_trustbaritem",
    "footer_link_create": "products.add_footerlink",
    "footer_link_update": "products.change_footerlink",
    "testimonial_create": "products.add_testimonial",
    "testimonial_update": "products.change_testimonial",
    "lookbook_create": "cms.add_lookbook",
    "lookbook_update": "cms.change_lookbook",
    "lookbook_item_create": "cms.add_lookbookitem",
    "lookbook_item_update": "cms.change_lookbookitem",
    "blog_category_create": "cms.add_blogcategory",
    "blog_category_update": "cms.change_blogcategory",
    "blog_author_create": "cms.add_blogauthor",
    "blog_author_update": "cms.change_blogauthor",
    "blog_tag_create": "cms.add_blogtag",
    "blog_tag_update": "cms.change_blogtag",
    "product_size_create": "products.add_productsize",
    "product_size_update": "products.change_productsize",
    "product_badge_create": "cms.add_productbadge",
    "product_badge_update": "cms.change_productbadge",
    "product_label_create": "cms.add_productlabel",
    "product_label_update": "cms.change_productlabel",
    "care_instruction_create": "cms.add_careinstruction",
    "care_instruction_update": "cms.change_careinstruction",
    "size_chart_create": "cms.add_sizechart",
    "size_chart_update": "cms.change_sizechart",
    "instagram_item_create": "products.add_instagramfeeditem",
    "instagram_item_update": "products.change_instagramfeeditem",
    "promo_config_create": "products.add_promotionalbannerconfig",
    "promo_config_update": "products.change_promotionalbannerconfig",
    "collection_create": "cms.add_collection",
    "collection_update": "cms.change_collection",
    "collection_product_create": "cms.add_collectionproduct",
    "collection_product_update": "cms.change_collectionproduct",
    "testimonial_extended_create": "cms.add_testimonialextended",
    "testimonial_extended_update": "cms.change_testimonialextended",
}

ACTION_LABELS = {
    "product_create": "Create product",
    "product_update": "Update product",
    "theme_update": "Update storefront theme",
    "homepage_section_create": "Create homepage section",
    "homepage_section_update": "Update homepage section",
    "announcement_update": "Update announcement bar",
    "banner_create": "Create promotional banner",
    "banner_update": "Update promotional banner",
    "content_page_create": "Create content page",
    "content_page_update": "Update content page",
    "website_settings_update": "Update website settings",
    "category_create": "Create product category",
    "category_update": "Update product category",
    "navigation_create": "Create navigation link",
    "navigation_update": "Update navigation link",
    "blog_post_create": "Create blog post",
    "blog_post_update": "Update blog post",
    "faq_category_create": "Create FAQ category",
    "faq_category_update": "Update FAQ category",
    "faq_item_create": "Create FAQ item",
    "faq_item_update": "Update FAQ item",
    "legal_page_create": "Create legal page",
    "legal_page_update": "Update legal page",
    "popup_create": "Create promotional popup",
    "popup_update": "Update promotional popup",
    "hero_slide_create": "Create homepage hero slide",
    "hero_slide_update": "Update homepage hero slide",
    "seo_update": "Update page SEO settings",
    "brand_create": "Create brand",
    "brand_update": "Update brand",
    "shop_category_create": "Create shop-by-category tile",
    "shop_category_update": "Update shop-by-category tile",
    "trust_item_create": "Create trust-bar item",
    "trust_item_update": "Update trust-bar item",
    "footer_link_create": "Create footer link",
    "footer_link_update": "Update footer link",
    "testimonial_create": "Create customer testimonial",
    "testimonial_update": "Update customer testimonial",
    "lookbook_create": "Create lookbook",
    "lookbook_update": "Update lookbook",
    "lookbook_item_create": "Create lookbook item",
    "lookbook_item_update": "Update lookbook item",
    "blog_category_create": "Create blog category",
    "blog_category_update": "Update blog category",
    "blog_author_create": "Create blog author",
    "blog_author_update": "Update blog author",
    "blog_tag_create": "Create blog tag",
    "blog_tag_update": "Update blog tag",
    "product_size_create": "Add product size",
    "product_size_update": "Update product size",
    "product_badge_create": "Create product badge",
    "product_badge_update": "Update product badge",
    "product_label_create": "Create product label",
    "product_label_update": "Update product label",
    "care_instruction_create": "Create care instruction",
    "care_instruction_update": "Update care instruction",
    "size_chart_create": "Create size chart",
    "size_chart_update": "Update size chart",
    "instagram_item_create": "Create Instagram feed item",
    "instagram_item_update": "Update Instagram feed item",
    "promo_config_create": "Create promotional image configuration",
    "promo_config_update": "Update promotional image configuration",
    "collection_create": "Create storefront collection",
    "collection_update": "Update storefront collection",
    "collection_product_create": "Add product to collection",
    "collection_product_update": "Update collection product order",
    "testimonial_extended_create": "Add testimonial details",
    "testimonial_extended_update": "Update testimonial details",
}

ACTION_MODELS = {
    "banner_create": PromoBanner,
    "product_update": Product,
    "homepage_section_create": HomepageSection,
    "content_page_create": ContentPage,
    "homepage_section_update": HomepageSection,
    "banner_update": PromoBanner,
    "content_page_update": ContentPage,
    "category_create": Category,
    "category_update": Category,
    "navigation_create": SiteNavigation,
    "navigation_update": SiteNavigation,
    "blog_post_create": BlogPost,
    "blog_post_update": BlogPost,
    "faq_category_create": FAQCategory,
    "faq_category_update": FAQCategory,
    "faq_item_create": FAQItem,
    "faq_item_update": FAQItem,
    "legal_page_create": LegalPage,
    "legal_page_update": LegalPage,
    "popup_create": PromotionalPopup,
    "popup_update": PromotionalPopup,
    "hero_slide_create": HeroSlide,
    "hero_slide_update": HeroSlide,
    "seo_update": SEOSettings,
    "brand_create": Brand,
    "brand_update": Brand,
    "shop_category_create": ShopByCategoryItem,
    "shop_category_update": ShopByCategoryItem,
    "trust_item_create": TrustBarItem,
    "trust_item_update": TrustBarItem,
    "footer_link_create": FooterLink,
    "footer_link_update": FooterLink,
    "testimonial_create": Testimonial,
    "testimonial_update": Testimonial,
    "lookbook_create": Lookbook,
    "lookbook_update": Lookbook,
    "lookbook_item_create": LookbookItem,
    "lookbook_item_update": LookbookItem,
    "blog_category_create": BlogCategory,
    "blog_category_update": BlogCategory,
    "blog_author_create": BlogAuthor,
    "blog_author_update": BlogAuthor,
    "blog_tag_create": BlogTag,
    "blog_tag_update": BlogTag,
    "product_size_create": ProductSize,
    "product_size_update": ProductSize,
    "product_badge_create": ProductBadge,
    "product_badge_update": ProductBadge,
    "product_label_create": ProductLabel,
    "product_label_update": ProductLabel,
    "care_instruction_create": CareInstruction,
    "care_instruction_update": CareInstruction,
    "size_chart_create": SizeChart,
    "size_chart_update": SizeChart,
    "instagram_item_create": InstagramFeedItem,
    "instagram_item_update": InstagramFeedItem,
    "promo_config_create": PromotionalBannerConfig,
    "promo_config_update": PromotionalBannerConfig,
    "collection_create": Collection,
    "collection_update": Collection,
    "collection_product_create": CollectionProduct,
    "collection_product_update": CollectionProduct,
    "testimonial_extended_create": TestimonialExtended,
    "testimonial_extended_update": TestimonialExtended,
}

CREATE_KINDS = {
    "product_create",
    "homepage_section_create",
    "banner_create",
    "content_page_create",
    "category_create",
    "navigation_create",
    "blog_post_create",
    "faq_category_create",
    "faq_item_create",
    "legal_page_create",
    "popup_create",
    "hero_slide_create",
    "brand_create",
    "shop_category_create",
    "trust_item_create",
    "footer_link_create",
    "testimonial_create",
    "lookbook_create",
    "lookbook_item_create",
    "blog_category_create", "blog_author_create", "blog_tag_create",
    "product_size_create", "product_badge_create", "product_label_create",
    "care_instruction_create", "size_chart_create", "instagram_item_create", "promo_config_create",
    "collection_create", "collection_product_create", "testimonial_extended_create",
}

UPDATE_KINDS = {
    "product_update",
    "homepage_section_update",
    "banner_update",
    "content_page_update",
    "category_update",
    "navigation_update",
    "blog_post_update",
    "faq_category_update",
    "faq_item_update",
    "legal_page_update",
    "popup_update",
    "hero_slide_update",
    "seo_update",
    "brand_update",
    "shop_category_update",
    "trust_item_update",
    "footer_link_update",
    "testimonial_update",
    "lookbook_update",
    "lookbook_item_update",
    "blog_category_update", "blog_author_update", "blog_tag_update",
    "product_size_update", "product_badge_update", "product_label_update",
    "care_instruction_update", "size_chart_update", "instagram_item_update", "promo_config_update",
    "collection_update", "collection_product_update", "testimonial_extended_update",
}

DELETE_KINDS = set()
for _update_kind in UPDATE_KINDS:
    _model = ACTION_MODELS.get(_update_kind)
    if _model is None:
        continue
    _delete_kind = f"{_update_kind[:-7]}_delete"
    DELETE_KINDS.add(_delete_kind)
    ACTION_MODELS[_delete_kind] = _model
    ACTION_PERMISSIONS[_delete_kind] = f"{_model._meta.app_label}.delete_{_model._meta.model_name}"
    ACTION_LABELS[_delete_kind] = f"Delete {_model._meta.verbose_name}"

IMAGE_FIELD_MAP = {
    "banner_create": ["desktop_image", "mobile_image"],
    "banner_update": ["desktop_image", "mobile_image"],
    "theme_update": ["logo", "favicon"],
    "homepage_section_create": ["bg_image"],
    "homepage_section_update": ["bg_image"],
    "website_settings_update": ["og_image"],
    "seo_update": ["og_image"],
    "brand_create": ["logo"],
    "brand_update": ["logo"],
    "shop_category_create": ["desktop_image", "mobile_image"],
    "shop_category_update": ["desktop_image", "mobile_image"],
    "lookbook_create": ["cover_image"],
    "lookbook_update": ["cover_image"],
    "lookbook_item_create": ["image"],
    "lookbook_item_update": ["image"],
    "category_create": ["image"],
    "category_update": ["image"],
    "blog_post_create": ["featured_image"],
    "blog_post_update": ["featured_image"],
    "popup_create": ["image"],
    "popup_update": ["image"],
    "hero_slide_create": ["desktop_image", "mobile_image"],
    "hero_slide_update": ["desktop_image", "mobile_image"],
    "blog_author_create": ["photo"],
    "blog_author_update": ["photo"],
    "size_chart_create": ["image"],
    "size_chart_update": ["image"],
    "instagram_item_create": ["image"],
    "instagram_item_update": ["image"],
    "promo_config_create": ["desktop_image", "mobile_image"],
    "promo_config_update": ["desktop_image", "mobile_image"],
    "collection_create": ["image"],
    "collection_update": ["image"],
    "testimonial_extended_create": ["photo"],
    "testimonial_extended_update": ["photo"],
}
IMAGE_KINDS = {"product_create", "product_update", "banner_create", "banner_update", *IMAGE_FIELD_MAP}
PAGE_HTML_TAGS = {
    "a", "blockquote", "br", "div", "em", "h2", "h3", "h4", "hr", "li",
    "ol", "p", "strong", "ul",
}
PAGE_HTML_ATTRIBUTES = {"a": ["href", "title", "target", "rel"]}


def _clean_page_content(content):
    return bleach.clean(
        str(content),
        tags=PAGE_HTML_TAGS,
        attributes=PAGE_HTML_ATTRIBUTES,
        protocols={"http", "https", "mailto"},
        strip=True,
    )


class ProposalError(Exception):
    pass


def allowed_kinds(user):
    return [
        kind for kind, permission in ACTION_PERMISSIONS.items()
        if user.has_perm(permission)
    ]


def field_definitions():
    definitions = {}
    for kind, names in ACTION_FIELDS.items():
        definitions[kind] = [
            {"name": name, **VALUE_FIELDS[name]}
            for name in names
        ]
    return definitions


def build_site_context(user):
    write_capabilities = allowed_kinds(user)
    capabilities = set(write_capabilities)
    capabilities.update(
        f"{kind[:-7]}_update"
        for kind in write_capabilities
        if kind.endswith("_delete")
    )
    context = {
        "can_create_category": user.has_perm("products.add_category"),
        "capabilities": [
            {"kind": kind, "label": ACTION_LABELS[kind]}
            for kind in write_capabilities
        ],
    }

    if {"product_create", "product_update", "product_size_create", "product_size_update", "category_create", "category_update", "shop_category_create", "shop_category_update", "size_chart_create", "size_chart_update"}.intersection(capabilities):
        context["categories"] = list(
            Category.objects.order_by("display_order", "name").values("id", "name", "slug")[:200]
        )
    if {"product_create", "product_update", "product_size_create", "product_size_update", "lookbook_item_create", "lookbook_item_update", "collection_product_create", "collection_product_update"}.intersection(capabilities):
        context["products"] = [
            {
                "id": product.id,
                "name": product.name,
                "brand": product.brand,
                "category_id": product.category_id,
                "category": product.category.name,
                "material": product.material,
                "condition": product.condition,
                "price": str(product.price),
                "stock": product.stock,
                "description": product.description[:800],
                "is_featured": product.is_featured,
                "has_primary_image": bool(product.image),
                "gallery_image_ids": list(product.images.values_list("id", flat=True)),
            }
            for product in Product.objects.select_related("category").prefetch_related("images").order_by("-created_at")[:60]
        ]

    if "theme_update" in capabilities:
        theme = ThemeSettings.objects.filter(pk=1).first() or ThemeSettings()
        theme_fields = ACTION_FIELDS["theme_update"]
        context["theme"] = {name: getattr(theme, name) for name in theme_fields}

    if {"homepage_section_create", "homepage_section_update", "homepage_section_delete", "hero_slide_create", "hero_slide_update", "hero_slide_delete", "shop_category_create", "shop_category_update", "shop_category_delete", "trust_item_create", "trust_item_update", "trust_item_delete", "footer_link_create", "footer_link_update", "footer_link_delete", "promo_config_create", "promo_config_update", "promo_config_delete"}.intersection(capabilities):
        context["homepage_sections"] = list(
            HomepageSection.objects.order_by("display_order").values(
                "id", "section_type", "title", "subtitle", "overline", "is_active", "display_order",
                "padding_top", "padding_bottom", "margin", "bg_color", "animation", "border_radius",
                "container_width", "full_width", "hide_on_mobile", "hide_on_tablet", "hide_on_desktop", "anchor_id",
            )[:60]
        )

    if {"blog_post_create", "blog_post_update", "blog_category_create", "blog_category_update", "blog_author_create", "blog_author_update", "blog_tag_create", "blog_tag_update"}.intersection(capabilities):
        context["blog_categories"] = list(BlogCategory.objects.filter(is_active=True).order_by("name").values("id", "name")[:100])
        context["blog_authors"] = list(BlogAuthor.objects.filter(is_active=True).order_by("name").values("id", "name")[:100])
        context["blog_tags"] = list(BlogTag.objects.order_by("name").values("id", "name", "slug")[:200])
        context["blog_posts"] = list(
            BlogPost.objects.order_by("-updated_at").values("id", "title", "slug", "category_id", "author_id", "is_published", "is_featured")[:60]
        )

    if {"product_size_create", "product_size_update"}.intersection(capabilities):
        context["product_sizes"] = list(
            ProductSize.objects.select_related("product").order_by("product__name", "size").values(
                "id", "product_id", "size", "stock"
            )[:300]
        )

    if {"product_badge_create", "product_badge_update"}.intersection(capabilities):
        context["product_badges"] = list(ProductBadge.objects.order_by("name").values("id", "name", "icon", "is_active")[:100])
    if {"product_label_create", "product_label_update"}.intersection(capabilities):
        context["product_labels"] = list(ProductLabel.objects.order_by("name").values("id", "name", "slug", "color", "bg_color", "is_active")[:100])
    if {"care_instruction_create", "care_instruction_update"}.intersection(capabilities):
        context["care_instructions"] = list(CareInstruction.objects.order_by("display_order").values("id", "name", "description", "icon", "is_active", "display_order")[:100])
    if {"size_chart_create", "size_chart_update"}.intersection(capabilities):
        context["size_charts"] = list(SizeChart.objects.order_by("name").values("id", "name", "category_id", "description", "is_active")[:100])
    if {"instagram_item_create", "instagram_item_update"}.intersection(capabilities):
        context["instagram_items"] = list(InstagramFeedItem.objects.order_by("display_order").values("id", "link", "is_active", "display_order")[:100])
    if {"promo_config_create", "promo_config_update"}.intersection(capabilities):
        context["promo_configs"] = list(PromotionalBannerConfig.objects.select_related("section").order_by("section__display_order").values("id", "section_id", "is_active")[:100])

    if {"faq_item_create", "faq_item_update"}.intersection(capabilities):
        context["faq_categories"] = list(FAQCategory.objects.filter(is_active=True).order_by("display_order", "name").values("id", "name")[:100])
        context["faq_items"] = [
            {**item, "answer": item["answer"][:1200]}
            for item in FAQItem.objects.order_by("category__display_order", "display_order").values(
                "id", "category_id", "question", "answer", "is_active", "display_order"
            )[:100]
        ]

    if {"category_create", "category_update"}.intersection(capabilities):
        context["category_records"] = [
            {**item, "description": item["description"][:800]}
            for item in Category.objects.order_by("display_order", "name").values(
                "id", "name", "slug", "description", "display_order"
            )[:100]
        ]

    if {"navigation_create", "navigation_update"}.intersection(capabilities):
        context["navigation_items"] = list(
            SiteNavigation.objects.order_by("placement", "display_order").values(
                "id", "label", "url", "placement", "parent_id", "is_active", "display_order"
            )[:100]
        )

    if {"legal_page_create", "legal_page_update"}.intersection(capabilities):
        context["legal_pages"] = list(
            LegalPage.objects.order_by("display_order", "title").values(
                "id", "title", "slug", "content", "is_active", "display_order"
            )[:60]
        )

    if {"popup_create", "popup_update"}.intersection(capabilities):
        context["popups"] = list(
            PromotionalPopup.objects.order_by("-updated_at").values("id", "title", "popup_type", "trigger", "is_active")[:40]
        )

    if {"hero_slide_create", "hero_slide_update"}.intersection(capabilities):
        context["hero_slides"] = list(
            HeroSlide.objects.select_related("section").order_by("section_id", "display_order").values(
                "id", "section_id", "title", "subtitle", "description", "button_text", "button_url",
                "overlay_opacity", "image_position_x", "image_position_y", "is_active", "display_order"
            )[:60]
        )

    if {"brand_create", "brand_update"}.intersection(capabilities):
        context["brands"] = list(Brand.objects.order_by("display_order", "name").values("id", "name", "slug", "is_active")[:100])

    if {"shop_category_create", "shop_category_update"}.intersection(capabilities):
        context["shop_category_items"] = list(
            ShopByCategoryItem.objects.select_related("category", "section").order_by("section_id", "display_order").values(
                "id", "section_id", "category_id", "headline", "label", "is_active", "display_order"
            )[:100]
        )

    if {"trust_item_create", "trust_item_update"}.intersection(capabilities):
        context["trust_items"] = list(
            TrustBarItem.objects.select_related("section").order_by("section_id", "display_order").values(
                "id", "section_id", "title", "description", "is_active", "display_order"
            )[:100]
        )

    if {"footer_link_create", "footer_link_update"}.intersection(capabilities):
        context["footer_links"] = list(
            FooterLink.objects.select_related("section").order_by("section_id", "display_order").values(
                "id", "section_id", "column_heading", "label", "url", "is_active", "display_order"
            )[:100]
        )

    if {"testimonial_create", "testimonial_update", "testimonial_extended_create", "testimonial_extended_update"}.intersection(capabilities):
        context["testimonials"] = [
            {**item, "review": item["review"][:800]}
            for item in Testimonial.objects.order_by("display_order").values(
                "id", "name", "review", "is_active", "display_order"
            )[:100]
        ]
    if {"testimonial_extended_create", "testimonial_extended_update"}.intersection(capabilities):
        context["extended_testimonials"] = list(
            TestimonialExtended.objects.select_related("testimonial").order_by("display_order").values(
                "id", "testimonial_id", "rating", "video_url", "display_order", "is_featured"
            )[:100]
        )

    if {"collection_create", "collection_update", "collection_product_create", "collection_product_update"}.intersection(capabilities):
        context["collections"] = list(
            Collection.objects.order_by("display_order", "name").values("id", "name", "slug", "is_active", "display_order")[:100]
        )
    if {"collection_product_create", "collection_product_update"}.intersection(capabilities):
        context["collection_products"] = list(
            CollectionProduct.objects.select_related("collection", "product").order_by("collection_id", "display_order").values(
                "id", "collection_id", "product_id", "display_order"
            )[:200]
        )

    if {"lookbook_create", "lookbook_update", "lookbook_item_create", "lookbook_item_update"}.intersection(capabilities):
        context["lookbooks"] = list(
            Lookbook.objects.order_by("display_order", "title").values("id", "title", "slug", "is_published", "display_order")[:60]
        )
    if {"lookbook_item_create", "lookbook_item_update"}.intersection(capabilities):
        context["lookbook_items"] = [
            {**item, "description": item["description"][:800]}
            for item in LookbookItem.objects.select_related("lookbook", "product").order_by("lookbook_id", "display_order").values(
                "id", "lookbook_id", "product_id", "title", "description", "is_active", "display_order"
            )[:100]
        ]

    if "seo_update" in capabilities:
        context["seo_settings"] = list(
            SEOSettings.objects.order_by("page_type").values(
                "id", "page_type", "meta_title", "meta_description", "meta_keywords", "canonical_url"
            )[:20]
        )

    if "announcement_update" in capabilities:
        announcement = AnnouncementBarConfig.objects.filter(pk=1).first() or AnnouncementBarConfig()
        context["announcement"] = {
            name: getattr(announcement, name)
            for name in ACTION_FIELDS["announcement_update"]
        }

    if {"banner_create", "banner_update"}.intersection(capabilities):
        context["banners"] = list(
            PromoBanner.objects.order_by("display_order", "-created_at").values(
                "id", "title", "subtitle", "description", "button_text", "button_url", "is_active", "display_order"
            )[:40]
        )

    if {"content_page_create", "content_page_update"}.intersection(capabilities):
        context["content_pages"] = list(
            ContentPage.objects.order_by("display_order", "title").values(
                "id", "title", "slug", "overline", "summary", "content", "meta_title", "meta_description", "is_active", "display_order"
            )[:60]
        )

    if "website_settings_update" in capabilities:
        website = WebsiteSettings.objects.filter(pk=1).first() or WebsiteSettings()
        context["website_settings"] = {
            name: getattr(website, name)
            for name in ACTION_FIELDS["website_settings_update"]
        }

    return context


def _model_for_action(kind):
    if kind == "theme_update":
        return ThemeSettings
    if kind == "announcement_update":
        return AnnouncementBarConfig
    if kind == "website_settings_update":
        return WebsiteSettings
    return ACTION_MODELS.get(kind)


def _instance_for_action(kind, record_id=None, lock=False):
    model = _model_for_action(kind)
    if model is None:
        return None
    manager = model.objects.select_for_update() if lock else model.objects
    if kind in {"theme_update", "announcement_update", "website_settings_update"}:
        return manager.filter(pk=1).first() or model()
    if record_id is None:
        return None
    try:
        return manager.get(pk=record_id)
    except model.DoesNotExist as exc:
        raise ProposalError(f"The selected {model._meta.verbose_name} no longer exists.") from exc


def _ensure_navigation_parent(parent_id, record_id=None):
    if not parent_id:
        return
    parent_id = int(parent_id)
    if record_id and parent_id == record_id:
        raise ProposalError("A navigation item cannot be its own parent.")
    parents = dict(SiteNavigation.objects.values_list("id", "parent_id"))
    visited = set()
    current_id = parent_id
    while current_id and current_id in parents:
        if current_id == record_id:
            raise ProposalError("Choose a parent outside this navigation item's descendants.")
        if current_id in visited:
            raise ProposalError("The navigation hierarchy contains a cycle. Fix it in admin first.")
        visited.add(current_id)
        current_id = parents[current_id]


def _normalise_before(instance, fields):
    if instance is None:
        return None
    result = {}
    for name in fields:
        value = getattr(instance, name, None)
        if hasattr(value, "all"):
            continue
        if value is None:
            result[name] = None
        elif hasattr(value, "isoformat"):
            result[name] = value.isoformat()
        elif isinstance(value, Decimal):
            result[name] = str(value)
        else:
            result[name] = value
    return result


def _delete_snapshot(instance):
    """Return review-safe identity and cascade counts for a pending deletion."""
    details = {}
    for name in (
        "section_type", "title", "subtitle", "overline", "name", "slug", "label", "url",
        "placement", "is_active", "display_order", "price", "stock", "category_id", "section_id",
    ):
        if not any(field.name == name for field in instance._meta.concrete_fields):
            continue
        value = getattr(instance, name, None)
        if value is None:
            continue
        details[name] = str(value)[:500] if isinstance(value, Decimal) else value

    related_records = []
    for relation in instance._meta.related_objects:
        accessor = relation.get_accessor_name()
        if not accessor:
            continue
        try:
            related = getattr(instance, accessor)
            count = related.count() if hasattr(related, "count") else int(related is not None)
        except (AttributeError, relation.related_model.DoesNotExist):
            count = 0
        if count:
            related_records.append({
                "type": str(relation.related_model._meta.verbose_name_plural),
                "count": count,
                "on_delete": getattr(relation.on_delete, "__name__", "unknown"),
            })

    return {
        "record": str(instance)[:300],
        "details": details,
        "related_records": related_records,
    }


def _image_reference(instance, field_name):
    image_value = getattr(instance, field_name, None)
    if not image_value:
        return ""
    return getattr(image_value, "name", None) or getattr(image_value, "public_id", None) or str(image_value)


def _validate_value_bounds(values):
    bounds = {
        "font_size_scale": (Decimal("0.8"), Decimal("1.5")),
        "line_height": (Decimal("0.8"), Decimal("3.0")),
        "footer_columns": (1, 6),
        "products_per_page": (1, 100),
        "overlay_opacity": (0, 100),
        "image_position_x": (0, 100),
        "image_position_y": (0, 100),
        "delay_seconds": (0, 86400),
        "scroll_percent": (0, 100),
    }
    for name, (minimum, maximum) in bounds.items():
        if name not in values:
            continue
        try:
            number = Decimal(str(values[name]))
        except (InvalidOperation, ValueError):
            raise ProposalError(f"Enter a valid number for {VALUE_FIELDS[name]['label']}.")
        if number < minimum or number > maximum:
            raise ProposalError(f"{VALUE_FIELDS[name]['label']} must be between {minimum} and {maximum}.")


def _action_summary(kind, values, instance):
    label = ACTION_LABELS[kind]
    if instance is not None:
        return f"{label}: {str(instance)[:300]}"
    title = next((values.get(name) for name in ("name", "title", "label", "question") if values.get(name)), "")
    return f"{label}: {str(title)[:300]}" if title else label


def normalise_actions(raw_actions, user, attachment_count):
    permitted = set(allowed_kinds(user))
    if len(raw_actions) > 10:
        raise ProposalError("A single preview can contain at most 10 changes.")

    normalised = []
    for raw in raw_actions:
        if not isinstance(raw, dict):
            raise ProposalError("The AI returned a malformed change.")
        kind = raw.get("kind")
        if kind not in permitted:
            raise ProposalError("Your admin account does not have permission for one of these changes.")

        record_id = raw.get("record_id")
        if kind in CREATE_KINDS:
            record_id = None
        elif kind in UPDATE_KINDS or kind in DELETE_KINDS:
            if not isinstance(record_id, int) or record_id <= 0:
                raise ProposalError("The AI did not identify a valid existing item for this change.")
        elif kind in {"theme_update", "announcement_update", "website_settings_update"}:
            record_id = 1

        values = raw.get("values") or {}
        if not isinstance(values, dict):
            raise ProposalError("The AI returned invalid change values.")
        values = {
            name: value for name, value in values.items()
            if name in ACTION_FIELDS[kind] and value is not None
        }
        _validate_value_bounds(values)
        if kind in {"navigation_create", "navigation_update"} and "parent_id" in values:
            _ensure_navigation_parent(values["parent_id"], record_id)
        if kind in {"content_page_create", "content_page_update", "blog_post_create", "blog_post_update", "legal_page_create", "legal_page_update"} and "content" in values:
            values["content"] = _clean_page_content(values["content"])

        image_indices = raw.get("image_indices") or []
        if not isinstance(image_indices, list) or len(image_indices) > 10:
            raise ProposalError("The AI returned invalid image assignments.")
        if kind not in IMAGE_KINDS and image_indices:
            raise ProposalError("This type of change cannot use uploaded images.")
        if kind in IMAGE_FIELD_MAP and len(image_indices) > len(IMAGE_FIELD_MAP[kind]):
            raise ProposalError("This change accepts fewer images than were assigned.")
        if any(not isinstance(index, int) or index < 0 or index >= attachment_count for index in image_indices):
            raise ProposalError("An image assignment does not match an uploaded photo.")

        instance = _instance_for_action(kind, record_id)
        if kind == "product_update" and "category_id" in values:
            if not Category.objects.filter(pk=values["category_id"]).exists():
                raise ProposalError("The selected category no longer exists.")
        if kind == "product_create" and values.get("category_id") is not None:
            if not Category.objects.filter(pk=values["category_id"]).exists():
                raise ProposalError("The selected category no longer exists.")
        if kind == "category_delete" and instance.products.exists():
            raise ProposalError("This category still contains products. Deactivate it instead, or move its products first.")
        if values.get("new_category_name") and not user.has_perm("products.add_category"):
            raise ProposalError("Your admin account cannot create a new category. Choose an existing one.")

        if kind in {"product_create", "product_update"} and not values and not image_indices:
            raise ProposalError("The product proposal contains no changes.")
        if kind not in {"product_create", "product_update"} and kind not in DELETE_KINDS and not values and not image_indices:
            raise ProposalError("The proposal contains no changes.")

        before = _normalise_before(instance, ACTION_FIELDS[kind])
        if kind in DELETE_KINDS:
            before = _delete_snapshot(instance)
        if kind in IMAGE_FIELD_MAP and instance is not None:
            before["image_names"] = {
                field_name: _image_reference(instance, field_name)
                for field_name in IMAGE_FIELD_MAP[kind]
            }
        if kind == "product_update":
            before["existing_image_count"] = int(bool(instance.image)) + instance.images.count()
            before["existing_image_ids"] = list(instance.images.values_list("id", flat=True))
            before["primary_image_name"] = instance.image.name if instance.image else ""
        if kind == "seo_update":
            before["page_type"] = instance.get_page_type_display()

        normalised.append({
            "kind": kind,
            "record_id": record_id,
            "summary": _action_summary(kind, values, instance),
            "values": values,
            "image_indices": image_indices,
            "replace_images": bool(raw.get("replace_images", False)) if kind == "product_update" else False,
            "before": before,
        })
    return normalised


def _clean_action_submission(stored_actions, submitted_actions, user, attachment_count):
    if not isinstance(submitted_actions, list) or len(submitted_actions) != len(stored_actions):
        raise ProposalError("The preview has changed. Generate a fresh preview before applying it.")

    clean_actions = []
    for original, submitted in zip(stored_actions, submitted_actions):
        if not isinstance(submitted, dict):
            raise ProposalError("The submitted preview is invalid.")
        if submitted.get("kind") != original["kind"] or submitted.get("record_id") != original["record_id"]:
            raise ProposalError("The submitted preview no longer matches the generated plan.")
        kind = original["kind"]
        if kind not in allowed_kinds(user):
            raise ProposalError("Your admin permission for one of these changes has been removed.")
        instance = _instance_for_action(kind, original["record_id"], lock=True)
        if instance is not None:
            current = _delete_snapshot(instance) if kind in DELETE_KINDS else _normalise_before(instance, ACTION_FIELDS[kind])
            if any(current.get(name) != original["before"].get(name) for name in current):
                raise ProposalError("This item changed after the preview was prepared. Review a fresh preview before applying.")
            if kind in IMAGE_FIELD_MAP:
                current_images = {
                    field_name: _image_reference(instance, field_name)
                    for field_name in IMAGE_FIELD_MAP[kind]
                }
                if current_images != original["before"].get("image_names"):
                    raise ProposalError("This item's images changed after the preview was prepared. Review a fresh preview before applying.")
            if kind == "product_update":
                image_state = {
                    "existing_image_count": int(bool(instance.image)) + instance.images.count(),
                    "existing_image_ids": list(instance.images.values_list("id", flat=True)),
                    "primary_image_name": instance.image.name if instance.image else "",
                }
                if any(image_state.get(name) != original["before"].get(name) for name in image_state):
                    raise ProposalError("The product photos changed after the preview was prepared. Review a fresh preview before applying.")
        values = submitted.get("values")
        if not isinstance(values, dict):
            raise ProposalError("The submitted preview values are invalid.")
        editable_fields = set(ACTION_FIELDS[kind]) if kind in CREATE_KINDS else set(original["values"])
        if kind == "product_update":
            editable_fields.add("category_id")
            if user.has_perm("products.add_category"):
                editable_fields.add("new_category_name")
        values = {
            name: value for name, value in values.items()
            if name in editable_fields and name in ACTION_FIELDS[kind] and value is not None
        }
        _validate_value_bounds(values)
        if kind in {"navigation_create", "navigation_update"} and "parent_id" in values:
            _ensure_navigation_parent(values["parent_id"], original["record_id"])
        if kind in {"content_page_create", "content_page_update", "blog_post_create", "blog_post_update", "legal_page_create", "legal_page_update"} and "content" in values:
            values["content"] = _clean_page_content(values["content"])
        for name, value in values.items():
            if VALUE_FIELDS[name]["type"] == "color" and value and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(value)):
                raise ProposalError(f"Enter a valid hex color for {VALUE_FIELDS[name]['label']}.")
        image_indices = submitted.get("image_indices", original["image_indices"])
        if not isinstance(image_indices, list) or len(image_indices) > (10 if kind.startswith("product_") else len(IMAGE_FIELD_MAP.get(kind, []))) or any(
            not isinstance(index, int) or index < 0 or index >= attachment_count
            for index in image_indices
        ):
            raise ProposalError("A selected image is no longer available.")
        if kind not in IMAGE_KINDS and image_indices:
            raise ProposalError("This change cannot use uploaded images.")
        replace_images = bool(submitted.get("replace_images", original["replace_images"]))
        if kind == "product_update" and replace_images and not image_indices:
            raise ProposalError("Select at least one replacement photo or turn off photo replacement.")
        clean_actions.append({
            **original,
            "values": values,
            "image_indices": image_indices,
            "replace_images": replace_images,
        })
    return clean_actions


def _required_value(values, name, label):
    value = values.get(name)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ProposalError(f"Enter {label} in the preview before confirming.")
    return value


def _resolve_product_category(values, user, created_categories):
    category_id = values.get("category_id")
    new_name = str(values.get("new_category_name") or "").strip()
    if category_id:
        try:
            category = Category.objects.get(pk=int(category_id))
        except (Category.DoesNotExist, TypeError, ValueError) as exc:
            raise ProposalError("Choose an existing category or enter a new category name.") from exc
        if new_name:
            raise ProposalError("Choose either an existing category or a new category, not both.")
        return category
    if not new_name:
        raise ProposalError("Choose a product category in the preview before confirming.")
    if not user.has_perm("products.add_category"):
        raise ProposalError("Your admin account cannot create a new category. Choose an existing one.")

    base_slug = slugify(new_name) or f"category-{uuid4().hex[:8]}"
    slug = base_slug
    suffix = 2
    while Category.objects.filter(slug=slug).exists():
        slug = f"{base_slug[:190]}-{suffix}"
        suffix += 1
    category = Category(name=new_name[:200], slug=slug)
    category.full_clean()
    category.save()
    created_categories.append(category)
    return category


def _file_bytes(proposal, image_index):
    attachment = list(proposal.attachments.all())[image_index]
    with private_upload_storage.open(attachment.storage_path, "rb") as uploaded:
        return attachment, uploaded.read()


def _save_uploaded_image(field_file, attachment, image_bytes, created_files):
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", attachment.original_name)[:180] or "upload.jpg"
    field_file.save(filename, ContentFile(image_bytes), save=False)
    created_files.append((field_file.storage, field_file.name))


def _save_product_photo(field_file, attachment, image_bytes, owner, price, created_files):
    """Add the administrator's price callout and preserve the styled image."""
    final_bytes = render_product_price_callout(image_bytes, price)
    _save_uploaded_image(field_file, attachment, final_bytes, created_files)
    owner.image_hash = compute_image_hash(BytesIO(final_bytes))
    owner.image_norm_version = NORMALIZATION_VERSION


def _set_cloudinary_upload(instance, field_name, attachment, image_bytes):
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", attachment.original_name)[:180] or "upload.jpg"
    setattr(instance, field_name, SimpleUploadedFile(filename, image_bytes, content_type="image/jpeg"))


def _cleanup_external_image(storage, path):
    if storage == "cloudinary":
        from cloudinary import uploader

        uploader.destroy(path)
    else:
        storage.delete(path)


def _parse_product_sizes(raw_sizes):
    """Parse administrator-entered size stock rows such as ``S: 2``."""
    if raw_sizes is None or (isinstance(raw_sizes, str) and not raw_sizes.strip()):
        return []
    if not isinstance(raw_sizes, str):
        raise ProposalError("Enter sizes one per line as SIZE: quantity.")

    rows = [row.strip() for row in re.split(r"[\r\n,]+", raw_sizes) if row.strip()]
    if len(rows) > 20:
        raise ProposalError("Enter no more than 20 product sizes.")

    sizes = []
    seen = set()
    for row in rows:
        match = re.fullmatch(r"(.{1,10}?)\s*[:=]\s*(\d+)", row)
        if not match:
            raise ProposalError("Enter each size as SIZE: quantity, for example M: 3.")
        size = match.group(1).strip().upper()
        key = size.casefold()
        if not size or len(size) > 10:
            raise ProposalError("Each product size must be 1 to 10 characters.")
        if key in seen:
            raise ProposalError(f"The size {size} is listed more than once.")
        seen.add(key)
        sizes.append((size, int(match.group(2))))
    return sizes


def _apply_product(action, proposal, user, created_files, scheduled_deletions, created_categories):
    kind = action["kind"]
    values = action["values"]
    if kind == "product_create":
        for name, label in (("name", "a product name"), ("brand", "a brand"), ("condition", "a condition"), ("price", "a price"), ("sizes", "size quantities")):
            _required_value(values, name, label)
        category = _resolve_product_category(values, user, created_categories)
        sizes = _parse_product_sizes(values.get("sizes"))
        stock = sum(size_stock for _, size_stock in sizes)
        if stock < 1:
            raise ProposalError("Enter at least one available item across the product sizes.")
        try:
            price = Decimal(str(values["price"]))
        except (InvalidOperation, ValueError) as exc:
            raise ProposalError("Enter a valid product price in the preview.") from exc
        product = Product(
            name=str(values["name"]).strip(),
            brand=str(values["brand"]).strip(),
            category=category,
            condition=values["condition"],
            material=str(values.get("material") or "").strip(),
            price=price,
            stock=stock,
            description=str(values.get("description") or ""),
            is_featured=bool(values.get("is_featured", False)),
        )
        product.full_clean()
        images = action["image_indices"]
        if images:
            attachment, image_bytes = _file_bytes(proposal, images[0])
            _save_product_photo(product.image, attachment, image_bytes, product, price, created_files)
        product.save()
        for size, size_stock in sizes:
            size_record = ProductSize(product=product, size=size, stock=size_stock)
            size_record.full_clean()
            size_record.save()
        for image_index in images[1:]:
            attachment, image_bytes = _file_bytes(proposal, image_index)
            gallery = ProductImage(product=product)
            _save_product_photo(gallery.image, attachment, image_bytes, gallery, price, created_files)
            gallery.save()
        return product, ADDITION

    product = Product.objects.get(pk=action["record_id"])
    if "category_id" in values or values.get("new_category_name"):
        product.category = _resolve_product_category(values, user, created_categories)
    for name in ("name", "brand", "condition", "material", "description", "is_featured", "stock"):
        if name in values:
            setattr(product, name, values[name])
    if "price" in values:
        try:
            product.price = Decimal(str(values["price"]))
        except (InvalidOperation, ValueError) as exc:
            raise ProposalError("Enter a valid product price in the preview.") from exc

    if action["replace_images"]:
        if product.image:
            scheduled_deletions.append((product.image.storage, product.image.name))
            product.image = ""
        for gallery in list(product.images.all()):
            if gallery.image:
                scheduled_deletions.append((gallery.image.storage, gallery.image.name))
            gallery.delete()

    images = action["image_indices"]
    if images:
        first_image_for_product = action["replace_images"] or not product.image
        if first_image_for_product:
            attachment, image_bytes = _file_bytes(proposal, images[0])
            _save_product_photo(product.image, attachment, image_bytes, product, product.price, created_files)
            images = images[1:]
    product.full_clean()
    product.save()
    for image_index in images:
        attachment, image_bytes = _file_bytes(proposal, image_index)
        gallery = ProductImage(product=product)
        _save_product_photo(gallery.image, attachment, image_bytes, gallery, product.price, created_files)
        gallery.save()
    return product, CHANGE


def _apply_regular_model(instance, kind, values, action, proposal, created_files, scheduled_deletions):
    if kind in {"navigation_create", "navigation_update"} and "parent_id" in values:
        _ensure_navigation_parent(values["parent_id"], action["record_id"])
    for name in ("url", "button_url", "link_url", "canonical_url"):
        if values.get(name):
            validate_safe_url(str(values[name]))
    if kind in {"content_page_create", "content_page_update", "blog_post_create", "blog_post_update", "legal_page_create", "legal_page_update"} and "content" in values:
        values["content"] = _clean_page_content(values["content"])
    for name, value in values.items():
        setattr(instance, name, value)

    uploaded_cloudinary_fields = []
    for image_position, field_name in enumerate(IMAGE_FIELD_MAP.get(kind, [])):
        if image_position >= len(action["image_indices"]):
            break
        field = instance._meta.get_field(field_name)
        previous_reference = _image_reference(instance, field_name)
        if previous_reference:
            if isinstance(field, CloudinaryField):
                scheduled_deletions.append(("cloudinary", previous_reference))
            else:
                field_file = getattr(instance, field_name)
                scheduled_deletions.append((field_file.storage, field_file.name))
        attachment, image_bytes = _file_bytes(proposal, action["image_indices"][image_position])
        if isinstance(field, CloudinaryField):
            _set_cloudinary_upload(instance, field_name, attachment, image_bytes)
            uploaded_cloudinary_fields.append(field_name)
        else:
            _save_uploaded_image(getattr(instance, field_name), attachment, image_bytes, created_files)

    instance.full_clean()
    instance.save()
    for field_name in uploaded_cloudinary_fields:
        new_reference = _image_reference(instance, field_name)
        if new_reference:
            created_files.append(("cloudinary", new_reference))
    return instance


def _log_change(user, instance, action_flag, description):
    LogEntry.objects.log_action(
        user_id=user.pk,
        content_type_id=ContentType.objects.get_for_model(instance).pk,
        object_id=str(instance.pk),
        object_repr=str(instance)[:200],
        action_flag=action_flag,
        change_message=description,
    )


def _schedule_deleted_media(instance, scheduled_deletions):
    collector = Collector(using=instance._state.db)
    collector.collect([instance])
    seen = set()
    for objects in collector.data.values():
        for obj in objects:
            for field in obj._meta.concrete_fields:
                value = getattr(obj, field.name, None)
                if isinstance(field, CloudinaryField):
                    reference = _image_reference(obj, field.name)
                    item = ("cloudinary", reference) if reference else None
                elif isinstance(field, FileField) and value and value.name:
                    item = (value.storage, value.name)
                else:
                    item = None
                if item and item not in seen:
                    seen.add(item)
                    scheduled_deletions.append(item)


def _apply_one(action, proposal, user, created_files, scheduled_deletions, created_categories):
    kind = action["kind"]
    values = dict(action["values"])

    if kind in DELETE_KINDS:
        model = _model_for_action(kind)
        instance = model.objects.select_for_update().get(pk=action["record_id"])
        if kind == "category_delete" and instance.products.exists():
            raise ProposalError("This category still contains products. Deactivate it instead, or move its products first.")
        name = str(instance)[:300]
        _schedule_deleted_media(instance, scheduled_deletions)
        _log_change(user, instance, DELETION, "Deleted through Syafra AI Assistant after administrator confirmation.")
        instance.delete()
        return {
            "kind": kind,
            "label": ACTION_LABELS[kind],
            "id": action["record_id"],
            "name": name,
            "admin_model": f"{model._meta.app_label}_{model._meta.model_name}",
        }
    if kind in {"product_create", "product_update"}:
        instance, action_flag = _apply_product(
            action, proposal, user, created_files, scheduled_deletions, created_categories
        )
    else:
        model = _model_for_action(kind)
        if kind in {"theme_update", "announcement_update", "website_settings_update"}:
            instance = model.objects.filter(pk=1).first() or model()
        elif kind in CREATE_KINDS:
            instance = model()
        else:
            instance = model.objects.get(pk=action["record_id"])
        instance = _apply_regular_model(
            instance, kind, values, action, proposal, created_files, scheduled_deletions
        )
        action_flag = ADDITION if kind in CREATE_KINDS else CHANGE

    _log_change(user, instance, action_flag, "Applied through Syafra AI Assistant after administrator confirmation.")
    parent_admin_ids = {
        "faq_item_create": getattr(instance, "category_id", None),
        "faq_item_update": getattr(instance, "category_id", None),
        "hero_slide_create": getattr(instance, "section_id", None),
        "hero_slide_update": getattr(instance, "section_id", None),
        "shop_category_create": getattr(instance, "section_id", None),
        "shop_category_update": getattr(instance, "section_id", None),
        "trust_item_create": getattr(instance, "section_id", None),
        "trust_item_update": getattr(instance, "section_id", None),
        "footer_link_create": getattr(instance, "section_id", None),
        "footer_link_update": getattr(instance, "section_id", None),
        "lookbook_item_create": getattr(instance, "lookbook_id", None),
        "lookbook_item_update": getattr(instance, "lookbook_id", None),
        "product_size_create": getattr(instance, "product_id", None),
        "product_size_update": getattr(instance, "product_id", None),
        "promo_config_create": getattr(instance, "section_id", None),
        "promo_config_update": getattr(instance, "section_id", None),
        "collection_product_create": getattr(instance, "collection_id", None),
        "collection_product_update": getattr(instance, "collection_id", None),
    }
    return {
        "kind": kind,
        "label": ACTION_LABELS[kind],
        "id": instance.pk,
        "admin_object_id": parent_admin_ids.get(kind, instance.pk),
        "name": str(instance),
    }


def apply_confirmed_proposal(proposal, submitted_actions, user):
    attachments = list(proposal.attachments.all())
    actions = _clean_action_submission(
        proposal.actions, submitted_actions, user, len(attachments)
    )
    created_files = []
    scheduled_deletions = []
    created_categories = []
    results = []

    try:
        with transaction.atomic():
            for action in actions:
                results.append(_apply_one(
                    action, proposal, user, created_files, scheduled_deletions, created_categories
                ))
            proposal.applied_at = timezone.now()
            proposal.save(update_fields=["applied_at"])

            def finish_file_work():
                for storage, path in scheduled_deletions:
                    try:
                        _cleanup_external_image(storage, path)
                    except Exception:
                        logger.warning("Unable to clean replaced Syafra media file %s", path, exc_info=True)
                for attachment in attachments:
                    if attachment.storage_path:
                        try:
                            private_upload_storage.delete(attachment.storage_path)
                            attachment.storage_path = ""
                            attachment.save(update_fields=["storage_path"])
                        except Exception:
                            logger.warning("Unable to clean private Syafra agent upload %s", attachment.storage_path, exc_info=True)

            transaction.on_commit(finish_file_work)
    except Exception:
        for storage, path in created_files:
            try:
                _cleanup_external_image(storage, path)
            except Exception:
                logger.warning("Unable to clean rolled-back Syafra media file %s", path, exc_info=True)
        raise

    return results


def discard_proposal_files(proposal):
    for attachment in proposal.attachments.all():
        if attachment.storage_path:
            private_upload_storage.delete(attachment.storage_path)
    proposal.delete()


def expire_pending_proposals(user=None):
    queryset = AgentProposal.objects.filter(applied_at__isnull=True, expires_at__lte=timezone.now())
    if user is not None:
        queryset = queryset.filter(user=user)
    for proposal in queryset.prefetch_related("attachments"):
        discard_proposal_files(proposal)


def public_action(action):
    public_before = {
        name: value for name, value in (action["before"] or {}).items()
        if name not in {"existing_image_ids", "primary_image_name", "image_names"}
    }
    return {
        "kind": action["kind"],
        "record_id": action["record_id"],
        "summary": action["summary"],
        "values": action["values"],
        "image_indices": action["image_indices"],
        "replace_images": action["replace_images"],
        "before": public_before,
    }

from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig


class SyafraAdminSite(AdminSite):
    site_header = "SYAFRA Store Admin"
    site_title = "SYAFRA Admin"
    index_title = "Store workspace"

    app_order = (
        "products", "orders", "cart", "wishlist", "cms", "accounts", "auth", "contenttypes",
    )
    app_names = {
        "products": "Store",
        "orders": "Orders & Payments",
        "cart": "Cart",
        "wishlist": "Wishlist",
        "cms": "Website Content",
        "accounts": "Customer & Email Tools",
        "auth": "Access Control",
    }
    model_order = {
        "products": (
            "Product", "Category", "ProductCollection", "HomepageSection",
            "ContentPage", "ContactMessage", "Testimonial", "InstagramFeedItem",
            "NewsletterSubscriber", "ThemeSettings", "WebsiteSettings",
        ),
        "orders": ("Order", "OrderItem", "Payment", "PaymentSettings", "WhatsAppSettings"),
        "cms": (
            "SiteNavigation", "Collection", "Brand", "FAQCategory", "BlogPost",
            "BlogCategory", "Lookbook", "LegalPage", "SEOSettings", "CareInstruction",
            "SizeChart", "ThemeBackup",
        ),
    }
    hidden_from_index = {
        ("cms", "announcementbarconfig"),
        ("cms", "promobanner"),
        ("cms", "promotionalpopup"),
        ("cms", "productbadge"),
        ("cms", "productlabel"),
        ("cms", "testimonialextended"),
    }

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        filtered = []
        for app in app_list:
            label = app["app_label"]
            if label in self.app_names:
                app["name"] = self.app_names[label]
            app["models"] = [
                model for model in app["models"]
                if (label, model["object_name"].lower()) not in self.hidden_from_index
            ]
            if not app["models"]:
                continue
            preferred = self.model_order.get(label, ())
            order = {name.lower(): index for index, name in enumerate(preferred)}
            app["models"].sort(key=lambda model: (
                order.get(model["object_name"].lower(), len(order)),
                model["name"].casefold(),
            ))
            filtered.append(app)

        app_order = {label: index for index, label in enumerate(self.app_order)}
        filtered.sort(key=lambda app: (
            app_order.get(app["app_label"], len(app_order)), app["name"].casefold(),
        ))
        return filtered


class SyafraAdminConfig(AdminConfig):
    default_site = "syafra.admin.SyafraAdminSite"

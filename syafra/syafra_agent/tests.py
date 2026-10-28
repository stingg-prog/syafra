import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import InMemoryStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import ImageField
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from PIL import Image
from cloudinary.models import CloudinaryField
from products.models import Category, Product, ProductImage
from products.utils.image_normalizer import _studio_background, render_product_price_callout

from .actions import (
    ACTION_MODELS,
    ACTION_PERMISSIONS,
    DELETE_KINDS,
    IMAGE_FIELD_MAP,
    ProposalError,
    _model_for_action,
    _apply_product,
    _clean_page_content,
    _validate_value_bounds,
    _parse_product_sizes,
    field_definitions,
)
from .agent import OLLAMA_CONTEXT_LENGTH, _create_gemini_plan, _create_ollama_plan, AgentUnavailable
from .models import AgentAttachment, AgentProposal
from .schemas import ACTION_FIELDS, OUTPUT_SCHEMA, VALUE_FIELDS
from .views import UploadError, _apply_photo_edit_prompt, _prepare_upload, _require_admin_entered_product_facts, _require_bulk_product_photo_mapping, confirm_preview


class AgentSchemaTests(SimpleTestCase):
    def test_every_action_has_a_field_definition_and_model_or_singleton_handler(self):
        definitions = field_definitions()
        self.assertEqual(set(definitions), set(ACTION_FIELDS))
        self.assertTrue(set(ACTION_FIELDS).issubset(
            set(ACTION_MODELS) | {"product_create", "theme_update", "announcement_update", "website_settings_update"}
        ))
        self.assertTrue(all(name in VALUE_FIELDS for fields in ACTION_FIELDS.values() for name in fields))

    def test_model_permissions_match_action_models(self):
        for kind, model in ACTION_MODELS.items():
            verb = "delete" if kind.endswith("_delete") else "add" if kind.endswith("_create") else "change"
            expected = f"{model._meta.app_label}.{verb}_{model._meta.model_name}"
            self.assertEqual(ACTION_PERMISSIONS[kind], expected)

    def test_editable_content_supports_specific_record_deletions_and_homepage_creation(self):
        self.assertIn("homepage_section_create", ACTION_FIELDS)
        self.assertIn("homepage_section_delete", DELETE_KINDS)
        self.assertIn("homepage_section_delete", ACTION_MODELS)
        self.assertEqual(ACTION_FIELDS["homepage_section_delete"], [])
        self.assertNotIn("theme_delete", DELETE_KINDS)
        self.assertNotIn("announcement_delete", DELETE_KINDS)
        self.assertNotIn("custom_html", VALUE_FIELDS["section_type"]["schema"]["enum"])
        self.assertNotIn("custom_template", VALUE_FIELDS["section_type"]["schema"]["enum"])

    def test_action_fields_match_model_fields(self):
        for kind, names in ACTION_FIELDS.items():
            model = _model_for_action(kind)
            if model is None:
                continue
            model_fields = {field.name for field in model._meta.get_fields()}
            model_fields.update(getattr(field, "attname", field.name) for field in model._meta.get_fields())
            for name in names:
                if name not in {"new_category_name", "sizes"}:
                    self.assertIn(name, model_fields, f"{kind}.{name} is not a field on {model.__name__}")

    def test_image_assignments_target_image_fields(self):
        for kind, field_names in IMAGE_FIELD_MAP.items():
            model = ACTION_MODELS.get(kind)
            if model is None:
                model = _model_for_action(kind)
            for name in field_names:
                self.assertIsInstance(model._meta.get_field(name), (ImageField, CloudinaryField))

    def test_output_schema_only_exposes_each_actions_allowed_fields(self):
        branches = OUTPUT_SCHEMA["properties"]["actions"]["items"]["anyOf"]
        self.assertEqual(len(branches), len(ACTION_FIELDS))
        for branch in branches:
            kind = branch["properties"]["kind"]["enum"][0]
            values_schema = branch["properties"]["values"]
            self.assertEqual(set(values_schema["properties"]), set(ACTION_FIELDS[kind]))
            self.assertEqual(values_schema["required"], ACTION_FIELDS[kind])
            self.assertFalse(values_schema["additionalProperties"])


class AgentLocalModelTests(SimpleTestCase):
    def test_ollama_uses_the_bounded_context_for_local_vision(self):
        response = Mock()
        response.json.return_value = {
            "message": {
                "content": json.dumps({
                    "reply": "Ready",
                    "question": "",
                    "needs_clarification": False,
                    "actions": [],
                })
            }
        }
        with patch("syafra_agent.agent.requests.post", return_value=response) as post:
            _create_ollama_plan("Show homepage", [], {}, [])

        request = post.call_args.kwargs["json"]
        self.assertEqual(request["options"]["num_ctx"], OLLAMA_CONTEXT_LENGTH)
        self.assertEqual(request["format"], "json")

    @override_settings(SYAFRA_AGENT_GEMINI_API_KEY="test-key", SYAFRA_AGENT_GEMINI_MODEL="gemini-test")
    def test_gemini_sends_images_and_requests_json(self):
        response = Mock()
        response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": json.dumps({"reply": "Ready", "question": "", "needs_clarification": False, "actions": []})}]}}]
        }
        with patch("syafra_agent.agent.requests.post", return_value=response) as post:
            _create_gemini_plan("Create a listing", [], {}, [{"ai_bytes": b"photo"}])

        request = post.call_args.kwargs
        self.assertEqual(request["headers"]["x-goog-api-key"], "test-key")
        self.assertEqual(request["json"]["generationConfig"]["responseMimeType"], "application/json")
        image_part = request["json"]["contents"][0]["parts"][1]["inlineData"]
        self.assertEqual(image_part["mimeType"], "image/jpeg")
        self.assertTrue(image_part["data"])

    @override_settings(SYAFRA_AGENT_GEMINI_API_KEY="")
    def test_gemini_requires_server_api_key(self):
        with self.assertRaisesMessage(AgentUnavailable, "Cloud Gemini is not configured."):
            _create_gemini_plan("Create a listing", [], {}, [])


class AgentSafetyTests(SimpleTestCase):
    def test_apply_endpoint_requires_explicit_review_confirmation(self):
        request = RequestFactory().post("/admin/ai-assistant/confirm/", {"review_confirmed": "no"})
        request.user = SimpleNamespace(is_authenticated=True, is_active=True, is_staff=True)
        response = confirm_preview(request)
        self.assertEqual(response.status_code, 400)

    def test_page_content_removes_unsafe_markup(self):
        cleaned = _clean_page_content('<h2>New</h2><script>alert(1)</script><a href="javascript:alert(1)">Shop</a>')
        self.assertIn("<h2>New</h2>", cleaned)
        self.assertNotIn("<script>", cleaned)
        self.assertNotIn("javascript:", cleaned)

    def test_theme_value_bounds_reject_invalid_values(self):
        _validate_value_bounds({"font_size_scale": "1.2", "footer_columns": 4})
        with self.assertRaisesMessage(ProposalError, "Font size scale must be between 0.8 and 1.5."):
            _validate_value_bounds({"font_size_scale": "1.8"})

    def test_only_new_product_price_and_sizes_are_removed_until_admin_enters_them(self):
        actions = [
            {"kind": "product_create", "values": {"name": "Top", "price": "99"}},
            {"kind": "product_update", "values": {"price": "120"}},
        ]
        actions[0]["values"].update({"stock": 4, "condition": "new", "material": "Cotton", "sizes": "M: 4"})
        result = _require_admin_entered_product_facts(actions)
        for name in ("price", "stock", "sizes"):
            self.assertNotIn(name, result[0]["values"])
        for name in ("condition", "material"):
            self.assertIn(name, result[0]["values"])
        self.assertEqual(result[1]["values"]["price"], "120")

    def test_bulk_product_photo_mapping_requires_one_product_per_uploaded_photo(self):
        actions = [
            {"kind": "product_create", "image_indices": [0]},
            {"kind": "product_create", "image_indices": [1]},
        ]
        self.assertEqual(_require_bulk_product_photo_mapping(actions, 2), actions)
        with self.assertRaises(ProposalError):
            _require_bulk_product_photo_mapping(actions[:1], 2)

    def test_admin_size_stock_rows_are_parsed_and_normalized(self):
        self.assertEqual(_parse_product_sizes("s: 2\nM=3"), [("S", 2), ("M", 3)])

    def test_invalid_or_duplicate_size_stock_rows_are_rejected(self):
        with self.assertRaisesMessage(ProposalError, "Enter each size as SIZE: quantity, for example M: 3."):
            _parse_product_sizes("M: many")
        with self.assertRaisesMessage(ProposalError, "The size M is listed more than once."):
            _parse_product_sizes("m: 2\nM: 1")

    def test_image_upload_is_normalized_to_jpeg_for_analysis(self):
        source = BytesIO()
        Image.new("RGB", (64, 32), "#734b2f").save(source, format="PNG")
        upload = SimpleUploadedFile("product.png", source.getvalue(), content_type="image/png")
        with patch(
            "products.utils.image_normalizer._remove_background",
            side_effect=lambda image: Image.new("L", image.size, 255),
        ):
            prepared = _prepare_upload(upload)
        with Image.open(BytesIO(prepared["ai_bytes"])) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (64, 32))
        self.assertEqual(prepared["content_type"], "image/png")

    def test_non_raster_upload_is_rejected(self):
        upload = SimpleUploadedFile("product.svg", b"<svg></svg>", content_type="image/svg+xml")
        with self.assertRaises(UploadError):
            _prepare_upload(upload)


class ProductPhotoStyleTests(SimpleTestCase):
    def test_studio_background_uses_warm_neutral_colors(self):
        red, green, blue = _studio_background(64, 64).getpixel((32, 32))
        self.assertGreater(red, green)
        self.assertGreater(green, blue)

    def test_admin_price_callout_is_rendered_on_product_photo(self):
        source = BytesIO()
        Image.new("RGB", (2000, 2000), (222, 198, 168)).save(source, format="JPEG")
        result = render_product_price_callout(source.getvalue(), "1499")
        with Image.open(BytesIO(result)) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (2000, 2000))

    def test_prompt_editor_applies_local_photo_adjustments(self):
        source = Image.new("RGB", (20, 20), (100, 100, 100))
        edited, summary = _apply_photo_edit_prompt(source, "make it brighter and warmer")
        self.assertIn("brighter", summary)
        self.assertIn("warmer tone", summary)
        self.assertGreater(edited.getpixel((0, 0))[0], source.getpixel((0, 0))[0])

    def test_prompt_editor_rejects_unsupported_generative_edits(self):
        with self.assertRaisesMessage(ValueError, "This local editor supports brightness"):
            _apply_photo_edit_prompt(Image.new("RGB", (20, 20)), "put the shirt on a model")


class ProductPhotoEditViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="photo-editor",
            email="photo-editor@example.com",
            password="test-password",
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.storage = InMemoryStorage()
        image_bytes = BytesIO()
        Image.new("RGB", (20, 20), (100, 100, 100)).save(image_bytes, format="JPEG")
        stored_path = self.storage.save("product.jpg", ContentFile(image_bytes.getvalue()))
        self.proposal = AgentProposal.objects.create(
            user=self.user,
            prompt="Create a product",
            actions=[{"kind": "product_create", "image_indices": [0]}],
            expires_at=timezone.now() + timedelta(minutes=20),
        )
        self.attachment = AgentAttachment.objects.create(
            proposal=self.proposal,
            storage_path=stored_path,
            original_name="product.jpg",
            content_type="image/jpeg",
            size=len(image_bytes.getvalue()),
        )

    def test_prompt_edit_updates_only_the_pending_draft_photo(self):
        with patch("syafra_agent.views.private_upload_storage", self.storage):
            response = self.client.post(
                reverse("syafra_agent:edit-photo", args=[self.proposal.pk, self.attachment.pk]),
                {"prompt": "make it brighter"},
            )

        self.assertEqual(response.status_code, 200)
        self.attachment.refresh_from_db()
        self.assertNotEqual(self.attachment.storage_path, "product.jpg")
        self.assertEqual(self.proposal.applied_at, None)
        with self.storage.open(self.attachment.storage_path, "rb") as edited_file:
            with Image.open(edited_file) as edited_image:
                self.assertGreater(edited_image.getpixel((0, 0))[0], 100)

    def test_confirmed_product_action_saves_primary_and_gallery_photos(self):
        private_storage = InMemoryStorage()
        product_storage = InMemoryStorage()
        source = BytesIO()
        Image.new("RGB", (40, 40), (120, 80, 60)).save(source, format="JPEG")
        source_bytes = source.getvalue()
        for index in range(2):
            path = private_storage.save(f"source-{index}.jpg", ContentFile(source_bytes))
            AgentAttachment.objects.create(
                proposal=self.proposal,
                storage_path=path,
                original_name=f"source-{index}.jpg",
                content_type="image/jpeg",
                size=len(source_bytes),
            )
        category = Category.objects.create(name="Tops", slug="tops")
        action = {
            "kind": "product_create",
            "record_id": None,
            "values": {
                "name": "Summer Top",
                "brand": "Syafra",
                "condition": "new",
                "price": "149",
                "stock": 2,
                "category_id": category.pk,
                "sizes": "M: 2",
            },
            "image_indices": [1, 2],
            "replace_images": False,
        }
        with (
            patch("syafra_agent.actions.private_upload_storage", private_storage),
            patch.object(Product._meta.get_field("image"), "storage", product_storage),
            patch.object(ProductImage._meta.get_field("image"), "storage", product_storage),
        ):
            product, _ = _apply_product(action, self.proposal, self.user, [], [], [])

        self.assertTrue(product.image.name)
        self.assertTrue(product_storage.exists(product.image.name))
        gallery_photos = list(product.images.all())
        self.assertEqual(len(gallery_photos), 1)
        self.assertTrue(product_storage.exists(gallery_photos[0].image.name))

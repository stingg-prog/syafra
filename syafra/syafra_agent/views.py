import json
import logging
import os
import re
import warnings
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image, ImageEnhance, ImageOps, UnidentifiedImageError
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from products.utils.image_normalizer import normalize_product_image

from .actions import (
    ACTION_MODELS,
    ACTION_LABELS,
    ProposalError,
    apply_confirmed_proposal,
    allowed_kinds,
    build_site_context,
    discard_proposal_files,
    expire_pending_proposals,
    field_definitions,
    normalise_actions,
    public_action,
)
from .agent import AgentRequestTooLarge, AgentUnavailable, create_plan
from .models import AgentAttachment, AgentProposal, private_upload_storage

logger = logging.getLogger(__name__)

MAX_IMAGE_COUNT = 10
MAX_IMAGE_SIZE = 8 * 1024 * 1024
MAX_TOTAL_UPLOAD_SIZE = 20 * 1024 * 1024
MAX_AI_IMAGE_SIZE = 2_300_000
MAX_PROMPT_LENGTH = 12_000
MAX_HISTORY_LENGTH = 12

IMAGE_MIME_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class UploadError(Exception):
    pass


def _require_admin_entered_product_facts(actions):
    """Leave only price and per-size quantities for admin review."""
    admin_entered_fields = ("price", "stock", "sizes")
    for action in actions:
        if action["kind"] == "product_create":
            for name in admin_entered_fields:
                action["values"].pop(name, None)
    return actions


def _require_bulk_product_photo_mapping(actions, image_count):
    product_actions = [action for action in actions if action["kind"] == "product_create"]
    assigned_indices = []
    for action in product_actions:
        image_indices = action["image_indices"]
        if len(image_indices) != 1:
            raise ProposalError("Bulk mode needs exactly one uploaded photo for each new product.")
        assigned_indices.extend(image_indices)
    if len(product_actions) != image_count or sorted(assigned_indices) != list(range(image_count)):
        raise ProposalError("The assistant could not prepare one product draft per photo. Try fewer photos or use group mode.")
    if len(actions) != len(product_actions):
        raise ProposalError("Bulk photo mode only creates product drafts. Submit website edits separately.")
    return actions


def _prepare_upload(upload):
    if upload.size > MAX_IMAGE_SIZE:
        raise UploadError(f"{upload.name} exceeds the 8 MB image limit.")
    raw_bytes = upload.read()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(BytesIO(raw_bytes))
            image.verify()
        image = Image.open(BytesIO(raw_bytes))
        if image.format not in IMAGE_MIME_TYPES:
            raise UploadError(f"{upload.name} is not a JPEG, PNG or WebP image.")
        image = ImageOps.exif_transpose(image).convert("RGB")

        try:
            normalized_file = normalize_product_image(ContentFile(raw_bytes, name=upload.name))
            processed_bytes = normalized_file.read()
        except Exception as exc:
            logger.exception("Unable to normalize uploaded Syafra product photo")
            raise UploadError(f"{upload.name} could not be prepared. Try another photo.") from exc
        if not processed_bytes:
            raise UploadError(f"{upload.name} could not be prepared as a product photo.")
        try:
            with Image.open(BytesIO(processed_bytes)) as processed_image:
                processed_format = processed_image.format
        except (UnidentifiedImageError, OSError) as exc:
            raise UploadError(f"{upload.name} could not be prepared as a product photo.") from exc
        normalized_extensions = {"JPEG": ".jpg", "PNG": ".png"}
        if processed_format not in normalized_extensions:
            raise UploadError(f"{upload.name} could not be converted to a supported product photo.")

        image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        ai_buffer = BytesIO()
        image.save(ai_buffer, format="JPEG", quality=78, optimize=True)
        ai_bytes = ai_buffer.getvalue()
        if len(ai_bytes) > 500_000:
            ai_buffer = BytesIO()
            image.thumbnail((900, 900), Image.Resampling.LANCZOS)
            image.save(ai_buffer, format="JPEG", quality=68, optimize=True)
            ai_bytes = ai_buffer.getvalue()
        safe_name = Path(upload.name).name
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)[:220] or "product-image"
        safe_name = f"{Path(safe_name).stem}_syafra{normalized_extensions[processed_format]}"
        return {
            "name": safe_name,
            "content_type": IMAGE_MIME_TYPES[processed_format],
            "processed_bytes": processed_bytes,
            "ai_bytes": ai_bytes,
        }
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise UploadError(f"{upload.name} is not a valid image file.") from exc


def _clean_history(raw_history):
    if not raw_history:
        return []
    try:
        history = json.loads(raw_history)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ProposalError("The conversation history is invalid. Start a new message.") from exc
    if not isinstance(history, list):
        raise ProposalError("The conversation history is invalid. Start a new message.")
    clean_history = []
    for item in history[-MAX_HISTORY_LENGTH:]:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
            continue
        content = item.get("content")
        if isinstance(content, str) and content.strip():
            clean_history.append({"role": item["role"], "content": content[:4000]})
    return clean_history


def _attachment_response(proposal):
    return [
        {
            "index": index,
            "name": attachment.original_name,
            "url": reverse(
                "syafra_agent:attachment-preview",
                args=[proposal.pk, attachment.pk],
            ),
            "edit_url": reverse(
                "syafra_agent:edit-photo",
                args=[proposal.pk, attachment.pk],
            ),
        }
        for index, attachment in enumerate(proposal.attachments.all())
    ]


def _apply_photo_edit_prompt(image, prompt):
    """Apply a small, explicit set of local Pillow adjustments to a draft photo."""
    normalized = prompt.casefold()
    edited = image.convert("RGB")
    changes = []
    if any(term in normalized for term in ("black and white", "grayscale", "greyscale", "monochrome", "black-white")):
        edited = ImageOps.grayscale(edited).convert("RGB")
        changes.append("black and white")
    else:
        if any(term in normalized for term in ("bright", "lighter", "lighten", "light aakku", "velicham", "ബ്രൈറ്റ്")):
            edited = ImageEnhance.Brightness(edited).enhance(1.15)
            changes.append("brighter")
        if any(term in normalized for term in ("dark", "darker", "darken", "dark aakku", "irunda", "ഇരുണ്ട")):
            edited = ImageEnhance.Brightness(edited).enhance(0.85)
            changes.append("darker")
        if any(term in normalized for term in ("contrast", "contrast kootu", "കോൺട്രാസ്റ്റ്")):
            edited = ImageEnhance.Contrast(edited).enhance(1.15)
            changes.append("more contrast")
        if any(term in normalized for term in ("warm", "warmer", "warm aakku", "ചൂടുള്ള ടോൺ")):
            red, green, blue = edited.split()
            edited = Image.merge("RGB", (ImageEnhance.Brightness(red).enhance(1.06), green, ImageEnhance.Brightness(blue).enhance(0.92)))
            changes.append("warmer tone")
        if any(term in normalized for term in ("cool", "cooler", "cool aakku", "തണുത്ത ടോൺ")):
            red, green, blue = edited.split()
            edited = Image.merge("RGB", (ImageEnhance.Brightness(red).enhance(0.93), green, ImageEnhance.Brightness(blue).enhance(1.07)))
            changes.append("cooler tone")
        if any(term in normalized for term in ("saturat", "vivid", "vibrant", "color kootu", "niram kootu", "കൂടുതൽ നിറം")):
            edited = ImageEnhance.Color(edited).enhance(1.2)
            changes.append("more color")
        if any(term in normalized for term in ("sharp", "sharper", "sharpen", "sharp aakku", "ഷാർപ്പ്")):
            edited = ImageEnhance.Sharpness(edited).enhance(1.35)
            changes.append("sharper")
    if not changes:
        raise ValueError("This local editor supports brightness, contrast, warm/cool tone, saturation, sharpness, and black-and-white edits. It cannot add or remove objects or change the scene.")
    return edited, ", ".join(changes)


@staff_member_required
@require_GET
def index(request):
    if not allowed_kinds(request.user):
        return JsonResponse({"error": "Your staff account has no Syafra content-management permissions."}, status=403)
    expire_pending_proposals(request.user)
    return render(
        request,
        "admin/syafra_agent/assistant.html",
        {
            "field_definitions": field_definitions(),
            "history_limit": MAX_HISTORY_LENGTH,
            "agent_provider": settings.SYAFRA_AGENT_PROVIDER,
            "can_create_category": request.user.has_perm("products.add_category"),
        },
    )


@staff_member_required
@require_POST
def create_preview(request):
    expire_pending_proposals(request.user)
    prompt = request.POST.get("prompt", "").strip()
    if not prompt:
        return JsonResponse({"error": "Write what you want Syafra to change."}, status=400)
    if len(prompt) > MAX_PROMPT_LENGTH:
        return JsonResponse({"error": "Keep each request under 12,000 characters."}, status=413)

    uploads = request.FILES.getlist("images")
    product_photo_mode = request.POST.get("product_photo_mode", "group_items")
    if product_photo_mode not in {"group_items", "one_per_photo"}:
        return JsonResponse({"error": "Choose a valid product photo batch mode."}, status=400)
    if product_photo_mode == "one_per_photo" and not uploads:
        return JsonResponse({"error": "Upload at least one product photo for bulk mode."}, status=400)
    if len(uploads) > MAX_IMAGE_COUNT:
        return JsonResponse({"error": f"Upload no more than {MAX_IMAGE_COUNT} images at once."}, status=413)
    if sum(upload.size for upload in uploads) > MAX_TOTAL_UPLOAD_SIZE:
        return JsonResponse({"error": "The combined image upload must stay under 20 MB."}, status=413)

    try:
        history = _clean_history(request.POST.get("history", "[]"))
        prepared_images = [_prepare_upload(upload) for upload in uploads]
        if sum(len(image["ai_bytes"]) for image in prepared_images) > MAX_AI_IMAGE_SIZE:
            return JsonResponse({"error": "These images are too large to analyze together. Upload fewer or smaller photos."}, status=413)
        site_context = build_site_context(request.user)
        planning_prompt = prompt
        if product_photo_mode == "one_per_photo" and prepared_images:
            planning_prompt += (
                "\n\nBULK PRODUCT PHOTO MODE: Create exactly one new product listing for each uploaded photo. "
                "Do not group photos together. Product action 1 must use image index 0, action 2 index 1, "
                "and continue in order. Return only product_create actions and assign every uploaded image exactly once. "
                "Keep price and per-size stock quantities blank for the administrator. Fill the remaining product details "
                "from visible evidence, use Unbranded when no brand label is legible, and do not guess uncertain facts."
            )
        plan = create_plan(
            prompt=planning_prompt,
            history=history,
            context=site_context,
            prepared_images=prepared_images,
        )
        actions = _require_admin_entered_product_facts(
            normalise_actions(plan.get("actions", []), request.user, len(prepared_images))
        )
        if product_photo_mode == "one_per_photo" and prepared_images:
            _require_bulk_product_photo_mapping(actions, len(prepared_images))
        reply = str(plan.get("reply", ""))[:4000]
        question = str(plan.get("question") or "")[:2000]
        if not actions:
            return JsonResponse({
                "reply": reply,
                "question": question,
                "needs_clarification": bool(plan.get("needs_clarification")),
                "actions": [],
            })

        expiry = timezone.now() + timedelta(minutes=settings.SYAFRA_AGENT_PROPOSAL_TTL_MINUTES)
        proposal = AgentProposal.objects.create(
            user=request.user,
            prompt=prompt,
            reply=reply,
            actions=actions,
            expires_at=expiry,
        )
        try:
            for index, image in enumerate(prepared_images):
                extension = Path(image["name"]).suffix.lower() or ".img"
                path = private_upload_storage.save(
                    f"{proposal.pk}/{index:02d}{extension}",
                    ContentFile(image["processed_bytes"]),
                )
                AgentAttachment.objects.create(
                    proposal=proposal,
                    storage_path=path,
                    original_name=image["name"],
                    content_type=image["content_type"],
                    size=len(image["processed_bytes"]),
                )
        except Exception:
            discard_proposal_files(proposal)
            raise

        return JsonResponse({
            "proposal_id": str(proposal.pk),
            "reply": reply,
            "question": question,
            "needs_clarification": bool(plan.get("needs_clarification")),
            "actions": [public_action(action) for action in actions],
            "field_definitions": field_definitions(),
            "categories": site_context.get("categories", []),
            "choices": {
                **{
                    name: site_context.get(name, [])
                    for name in (
                        "blog_categories", "blog_authors", "faq_categories", "navigation_items",
                        "homepage_sections", "category_records", "hero_slides", "blog_posts",
                        "faq_items", "legal_pages", "popups", "seo_settings", "brands",
                        "shop_category_items", "trust_items", "footer_links", "testimonials",
                        "lookbooks", "lookbook_items",
                        "blog_tags", "product_sizes", "product_badges", "product_labels",
                        "care_instructions", "size_charts", "instagram_items", "promo_configs",
                        "extended_testimonials", "collections", "collection_products",
                    )
                },
                "products": [
                    {"id": product["id"], "name": product["name"]}
                    for product in site_context.get("products", [])
                ],
            },
            "can_create_category": request.user.has_perm("products.add_category"),
            "attachments": _attachment_response(proposal),
            "expires_at": proposal.expires_at.isoformat(),
        })
    except UploadError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except ProposalError as exc:
        return JsonResponse({"error": str(exc)}, status=422)
    except AgentRequestTooLarge as exc:
        return JsonResponse({"error": str(exc)}, status=413)
    except AgentUnavailable as exc:
        logger.warning("Syafra AI assistant unavailable: %s", exc)
        return JsonResponse({"error": str(exc)}, status=503)
    except Exception:
        logger.exception("Unable to prepare a Syafra AI preview")
        return JsonResponse({"error": "The preview could not be prepared. Try again or simplify the request."}, status=500)


@staff_member_required
@require_POST
def confirm_preview(request):
    if request.POST.get("review_confirmed") != "yes":
        return JsonResponse({"error": "Review the preview and explicitly confirm before applying changes."}, status=400)
    proposal_id = request.POST.get("proposal_id", "")
    try:
        submitted_actions = json.loads(request.POST.get("actions", "[]"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "The preview data is invalid. Generate it again."}, status=400)

    try:
        with transaction.atomic():
            proposal = get_object_or_404(
                AgentProposal.objects.select_for_update().prefetch_related("attachments"),
                pk=proposal_id,
                user=request.user,
            )
            if proposal.applied_at:
                return JsonResponse({"error": "This preview has already been applied."}, status=409)
            if proposal.is_expired:
                return JsonResponse({"error": "This preview expired. Generate a fresh preview before applying it."}, status=410)
            try:
                applied = apply_confirmed_proposal(proposal, submitted_actions, request.user)
            except (ProposalError, ValidationError) as exc:
                messages = getattr(exc, "messages", None)
                detail = "; ".join(messages) if messages else str(exc)
                return JsonResponse({"error": detail or "The preview contains invalid values."}, status=422)

        admin_routes = {
            "product_create": "products_product_change",
            "product_update": "products_product_change",
            "theme_update": "products_themesettings_change",
            "homepage_section_create": "products_homepagesection_change",
            "homepage_section_update": "products_homepagesection_change",
            "announcement_update": "cms_announcementbarconfig_change",
            "banner_create": "cms_promobanner_change",
            "banner_update": "cms_promobanner_change",
            "content_page_create": "products_contentpage_change",
            "content_page_update": "products_contentpage_change",
            "website_settings_update": "products_websitesettings_change",
            "category_create": "products_category_change",
            "category_update": "products_category_change",
            "navigation_create": "cms_sitenavigation_change",
            "navigation_update": "cms_sitenavigation_change",
            "blog_post_create": "cms_blogpost_change",
            "blog_post_update": "cms_blogpost_change",
            "faq_category_create": "cms_faqcategory_change",
            "faq_category_update": "cms_faqcategory_change",
            "faq_item_create": "cms_faqcategory_change",
            "faq_item_update": "cms_faqcategory_change",
            "legal_page_create": "cms_legalpage_change",
            "legal_page_update": "cms_legalpage_change",
            "popup_create": "cms_promotionalpopup_change",
            "popup_update": "cms_promotionalpopup_change",
            "hero_slide_create": "products_homepagesection_change",
            "hero_slide_update": "products_homepagesection_change",
            "seo_update": "cms_seosettings_change",
            "brand_create": "cms_brand_change",
            "brand_update": "cms_brand_change",
            "shop_category_create": "products_homepagesection_change",
            "shop_category_update": "products_homepagesection_change",
            "trust_item_create": "products_homepagesection_change",
            "trust_item_update": "products_homepagesection_change",
            "footer_link_create": "products_homepagesection_change",
            "footer_link_update": "products_homepagesection_change",
            "testimonial_create": "products_testimonial_change",
            "testimonial_update": "products_testimonial_change",
            "lookbook_create": "cms_lookbook_change",
            "lookbook_update": "cms_lookbook_change",
            "lookbook_item_create": "cms_lookbook_change",
            "lookbook_item_update": "cms_lookbook_change",
            "blog_category_create": "cms_blogcategory_change",
            "blog_category_update": "cms_blogcategory_change",
            "blog_author_create": "cms_blogauthor_change",
            "blog_author_update": "cms_blogauthor_change",
            "blog_tag_create": "cms_blogtag_change",
            "blog_tag_update": "cms_blogtag_change",
            "product_size_create": "products_product_change",
            "product_size_update": "products_product_change",
            "product_badge_create": "cms_productbadge_change",
            "product_badge_update": "cms_productbadge_change",
            "product_label_create": "cms_productlabel_change",
            "product_label_update": "cms_productlabel_change",
            "care_instruction_create": "cms_careinstruction_change",
            "care_instruction_update": "cms_careinstruction_change",
            "size_chart_create": "cms_sizechart_change",
            "size_chart_update": "cms_sizechart_change",
            "instagram_item_create": "products_instagramfeeditem_change",
            "instagram_item_update": "products_instagramfeeditem_change",
            "promo_config_create": "products_homepagesection_change",
            "promo_config_update": "products_homepagesection_change",
            "collection_create": "cms_collection_change",
            "collection_update": "cms_collection_change",
            "collection_product_create": "cms_collection_change",
            "collection_product_update": "cms_collection_change",
            "testimonial_extended_create": "cms_testimonialextended_change",
            "testimonial_extended_update": "cms_testimonialextended_change",
        }
        for item in applied:
            kind = item["kind"]
            if kind.startswith("product_") and not kind.endswith("_delete"):
                item["url"] = reverse("products:product_detail", args=[item["id"]])
            if kind.endswith("_delete"):
                model = ACTION_MODELS[kind]
                item.pop("admin_model", None)
                try:
                    item["admin_url"] = reverse(
                        f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
                    )
                except Exception:
                    item["admin_url"] = ""
                continue
            try:
                admin_object_id = item.pop("admin_object_id", item["id"])
                item["admin_url"] = reverse(
                    f"admin:{admin_routes[item['kind']]}",
                    args=[admin_object_id],
                )
            except Exception:
                item["admin_url"] = ""
        return JsonResponse({"applied": applied})
    except Http404:
        raise
    except Exception:
        logger.exception("Unable to apply a confirmed Syafra AI proposal")
        return JsonResponse({"error": "The change could not be applied. No confirmation was recorded."}, status=500)


@staff_member_required
@require_POST
def cancel_preview(request):
    try:
        proposal_id = UUID(request.POST.get("proposal_id", ""))
    except (AttributeError, TypeError, ValueError):
        return JsonResponse({"error": "The draft ID is invalid."}, status=400)
    proposal = get_object_or_404(
        AgentProposal.objects.prefetch_related("attachments"),
        pk=proposal_id,
        user=request.user,
        applied_at__isnull=True,
    )
    discard_proposal_files(proposal)
    return JsonResponse({"cancelled": True})


@staff_member_required
@require_POST
def edit_photo(request, proposal_id, attachment_id):
    prompt = request.POST.get("prompt", "").strip()
    if not prompt or len(prompt) > 500:
        return JsonResponse({"error": "Enter a photo edit prompt (up to 500 characters)."}, status=400)
    proposal = get_object_or_404(
        AgentProposal.objects.prefetch_related("attachments"),
        pk=proposal_id,
        user=request.user,
        applied_at__isnull=True,
        expires_at__gt=timezone.now(),
    )
    attachments = list(proposal.attachments.all())
    attachment = next((item for item in attachments if item.pk == attachment_id), None)
    if attachment is None:
        raise Http404
    attachment_index = attachments.index(attachment)
    if not any(
        action.get("kind") in {"product_create", "product_update"}
        and action.get("kind") in allowed_kinds(request.user)
        and attachment_index in action.get("image_indices", [])
        for action in proposal.actions
    ):
        return JsonResponse({"error": "Only a product photo in this preview can be edited."}, status=400)
    if not private_upload_storage.exists(attachment.storage_path):
        raise Http404
    try:
        with private_upload_storage.open(attachment.storage_path, "rb") as photo_file:
            with Image.open(photo_file) as source:
                edited, summary = _apply_photo_edit_prompt(source, prompt)
        output = BytesIO()
        edited.save(output, format="JPEG", quality=92, optimize=True)
        old_path = attachment.storage_path
        new_path = private_upload_storage.save(
            f"syafra-agent/{proposal.pk}/{attachment.pk}-edited-{timezone.now().timestamp()}.jpg",
            ContentFile(output.getvalue()),
        )
        attachment.storage_path = new_path
        attachment.original_name = f"{Path(attachment.original_name).stem}.jpg"
        attachment.content_type = "image/jpeg"
        attachment.size = len(output.getvalue())
        attachment.save(update_fields=["storage_path", "original_name", "content_type", "size"])
        private_upload_storage.delete(old_path)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=422)
    except (UnidentifiedImageError, OSError):
        return JsonResponse({"error": "This draft photo could not be edited. Prepare the preview again."}, status=422)
    return JsonResponse({
        "url": f"{reverse('syafra_agent:attachment-preview', args=[proposal.pk, attachment.pk])}?v={timezone.now().timestamp()}",
        "summary": summary,
    })


@staff_member_required
@require_GET
def attachment_preview(request, proposal_id, attachment_id):
    attachment = get_object_or_404(
        AgentAttachment.objects.select_related("proposal"),
        pk=attachment_id,
        proposal_id=proposal_id,
        proposal__user=request.user,
        proposal__applied_at__isnull=True,
        proposal__expires_at__gt=timezone.now(),
    )
    if not private_upload_storage.exists(attachment.storage_path):
        raise Http404
    response = FileResponse(
        private_upload_storage.open(attachment.storage_path, "rb"),
        content_type=attachment.content_type,
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Disposition"] = f'inline; filename="{os.path.basename(attachment.original_name)}"'
    return response

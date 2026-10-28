from django.urls import path

from . import views

app_name = "syafra_agent"

urlpatterns = [
    path("", views.index, name="index"),
    path("preview/", views.create_preview, name="create-preview"),
    path("confirm/", views.confirm_preview, name="confirm-preview"),
    path("cancel/", views.cancel_preview, name="cancel-preview"),
    path("image/<uuid:proposal_id>/<int:attachment_id>/edit/", views.edit_photo, name="edit-photo"),
    path("image/<uuid:proposal_id>/<int:attachment_id>/", views.attachment_preview, name="attachment-preview"),
]

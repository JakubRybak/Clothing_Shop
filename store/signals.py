from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ProductImage, ProductVariant
from .ai_utils import generate_brightness_for_variant

@receiver(post_save, sender=ProductImage)
def product_image_post_save(sender, instance, created, **kwargs):
    # Trigger brightness detection only when a new image is added or an existing one is updated
    # For simplicity, re-detect if it's new or if it's explicitly set as main (to ensure main image's brightness is detected)
    # The generate_brightness_for_variant function handles finding the main image
    
    # We only care about the variant that this image belongs to
    variant = instance.variant

    # Check if brightness is already set for this variant
    # This prevents re-detection if it's already there, unless forced
    # User scenario suggests brightness is not set on first image save.
    # OPTIMIZATION: Only trigger AI if this is the MAIN image.
    # This prevents 5 parallel API calls when uploading 5 images for one product.
    if instance.is_main and not variant.brightness:
        success, message = generate_brightness_for_variant(variant.id)
        if not success:
            # You might want to log this message to Django's logging system
            print(f"Warning: {message}")
    
    # Optional: if a non-main image is updated, we could re-detect as well,
    # but the current logic is fine as generate_brightness_for_variant
    # will find the main image of the variant.
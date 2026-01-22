from django.contrib import admin, messages
import nested_admin
from .models import Category, Product, ProductVariant, ProductImage
from .ai_utils import generate_product_features, generate_brightness_for_variant

# 1. Setup Inlines
class ProductImageInline(nested_admin.NestedTabularInline):
    model = ProductImage
    extra = 1
    # The fields color and brightness are now on the variant, not the image
    fields = ('image', 'is_main')

# This inline remains linked to Product
class ProductVariantInline(nested_admin.NestedTabularInline):
    model = ProductVariant
    extra = 1
    inlines = [ProductImageInline] # Nested inline for Product Images
    readonly_fields = ('brightness',) # Make brightness read-only

# 2. Configure Admins
@admin.register(Product)
class ProductAdmin(nested_admin.NestedModelAdmin):
    # ProductImageInline is removed from here because it's no longer a direct child of Product
    inlines = [ProductVariantInline]
    
    list_display = ('name', 'price', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('variants__color', 'variants__brightness', 'variants__size') # Added filters for variant attributes
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'categories', 'description', 'price')
        }),
        ('AI Generated Content', {
            'fields': ('ai_description', 'ai_tags', 'features'),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('features', 'created_at', 'updated_at')
    actions = ['generate_ai_features']

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        if formset.model == ProductVariant:
            for variant_form in formset.forms:
                if variant_form.instance.pk and variant_form.instance.id: # Check if the instance exists and has an ID
                    success, message = generate_brightness_for_variant(variant_form.instance.id)
                    if success:
                        messages.success(request, message)
                    else:
                        messages.warning(request, message)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        generate_product_features(form.instance.id)

    @admin.action(description="Regenerate AI Features (New Schema)")
    def generate_ai_features(self, request, queryset):
        for product in queryset:
            product.features = {}
            product.save(update_fields=['features'])
            generate_product_features(product.id)
        self.message_user(request, f"Successfully re-indexed {queryset.count()} products.")



@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

# We don't need to register ProductImage separately if it's only managed via inlines.
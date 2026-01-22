from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.db.models.functions import Lower
from django.urls import reverse
from urllib.parse import quote, urlencode
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
import json

from .models import Product, ProductVariant, Category
from .cart import Cart
from .ai_utils import load_category_schemas, process_search_query, api_detect_people, api_identify_items


def normalize_filter_value(value):
    if isinstance(value, str):
        cleaned_val = value.strip().lower()
        if cleaned_val == 'true':
            return True
        elif cleaned_val == 'false':
            return False
        return cleaned_val
    elif isinstance(value, list):
        return [normalize_filter_value(item) for item in value]
    return value

def _apply_all_query_filters(products_queryset, combined_colors, all_brightness_values, selected_sizes, selected_features, merged_negative_filters, merged_negative_colors, available_features_context):
    """
    Applies all variant, AI feature, and negative filters to a given queryset of products.
    """
    # --- REFACTORED Filtering on Variants ---
    if combined_colors and all_brightness_values:
        products_queryset = products_queryset.annotate(lower_color=Lower('variants__color')).filter(
            lower_color__in=combined_colors,
            variants__brightness__in=all_brightness_values
        ).distinct()
    elif combined_colors:
        products_queryset = products_queryset.annotate(lower_color=Lower('variants__color')).filter(lower_color__in=combined_colors).distinct()
    elif all_brightness_values:
        products_queryset = products_queryset.filter(variants__brightness__in=all_brightness_values).distinct()

    if selected_sizes:
        products_queryset = products_queryset.filter(variants__size__in=selected_sizes).distinct()

    # Apply AI Feature Filters (if any)
    for feature_key, feature_values in selected_features.items():
        if not feature_values: continue
        feature_attr_def = next((attr for attr in available_features_context if attr['key'] == feature_key), None)
        if feature_attr_def:
            if feature_attr_def.get('type') == 'boolean':
                for val in feature_values: products_queryset = products_queryset.filter(features__contains={feature_key: val})
            elif feature_attr_def.get('type') == 'select':
                q_objects = Q()
                for val in feature_values: q_objects |= Q(features__contains={feature_key: val})
                products_queryset = products_queryset.filter(q_objects)
            elif feature_attr_def.get('type') == 'string':
                q_objects = Q()
                for val in feature_values: q_objects |= Q(features__contains={feature_key: val})
                products_queryset = products_queryset.filter(q_objects)
    
    # Apply negative AI Feature Filters
    for feature_key, feature_values in merged_negative_filters.items():
        if not feature_values: continue
        feature_attr_def = next((attr for attr in available_features_context if attr['key'] == feature_key), None)
        if feature_attr_def:
            if feature_attr_def.get('type') == 'boolean':
                for val in feature_values: products_queryset = products_queryset.exclude(features__contains={feature_key: val})
            elif feature_attr_def.get('type') in ['select', 'string']:
                q_objects = Q()
                for val in feature_values: q_objects |= Q(features__contains={feature_key: val.lower()})
                products_queryset = products_queryset.exclude(q_objects)
    
    # Exclude products with variants matching negative colors
    if merged_negative_colors:
        products_queryset = products_queryset.exclude(variants__color__in=list(merged_negative_colors)).distinct()

    return products_queryset


def _assign_display_images(products, combined_colors, selected_brightness):
    """
    Assigns a display image to each product by finding the best matching *variant*
    based on the active filters, and then using that variant's main image.
    Fallbacks (tiers 4 and 5) are only applied if no color or brightness filters are active.
    """
    for product in products:
        # This is not a queryset, but a list of objects from the view
        variants = product.variants.all()
        
        best_variant = None
        
        # Tier 1: Find a variant that matches both color and brightness
        if combined_colors and selected_brightness:
            matches = [v for v in variants if v.color.lower() in combined_colors and v.brightness in selected_brightness]
            if matches:
                best_variant = matches[0]
        
        # Tier 2: If not, find a variant that matches the color (only if brightness not selected)
        if not best_variant and combined_colors and not selected_brightness:
            matches = [v for v in variants if v.color.lower() in combined_colors]
            if matches:
                best_variant = matches[0]

        # Tier 3: If not, find a variant that matches the brightness (only if color not selected)
        if not best_variant and selected_brightness and not combined_colors:
            matches = [v for v in variants if v.brightness in selected_brightness]
            if matches:
                best_variant = matches[0]

        # Tier 4 & 5: Absolute fallbacks (main image or first variant)
        # ONLY apply these fallbacks if NO color or brightness filters were active for display image selection
        if not best_variant and not combined_colors and not selected_brightness:
            # Tier 4: Find the first variant that has a main image
            for v in variants:
                if v.images.filter(is_main=True).exists():
                    best_variant = v
                    break
            
            # Tier 5: Absolute fallback to the first variant
            if not best_variant:
                best_variant = variants.first()
            
        # Assign the display image from the determined best variant
        if best_variant and best_variant.images.exists():
            # Store the best variant for potential use in product URLs
            product.display_variant = best_variant
            # Get the main image of that variant, or fallback to its first image
            main_image = next((img for img in best_variant.images.all() if img.is_main), best_variant.images.first())
            product.display_image = main_image

            # Store params for URL construction
            product.display_variant_params = {}
            if best_variant.color:
                product.display_variant_params['color'] = best_variant.color

        else:
            # If no suitable variant was found based on filters or fallbacks, display no image
            product.display_image = None
            product.display_variant = None
            product.display_variant_params = {} # Ensure it's always set, even if empty
            
    return products

def product_list(request, category_slug=None):
    category = None
    
    # --- Direct Category Switch (Visual Search) ---
    target_cat_name = request.GET.get('target_category')
    if target_cat_name:
        target_cat = Category.objects.filter(name__iexact=target_cat_name).first()
        if target_cat:
            base_url = reverse('product_list_by_category', args=[target_cat.slug])
            params = request.GET.copy()
            del params['target_category']
            query_string = params.urlencode()
            return redirect(f"{base_url}?{query_string}")

    # Optimize query by prefetching variants and their images
    products = Product.objects.all().prefetch_related('variants__images')
    
    # --- Search Logic (largely unchanged) ---
    search_queries = [q for q in request.GET.getlist('q') if q.strip()]
    ai_filters = {}
    ai_colors = []
    ai_search_summary = {}
    ai_detected_category = None
    query_contributions = []
    merged_negative_filters = {}
    merged_negative_colors = set()
    merged_attribute_suggestions = {}
    
    # --- Category Resolution & Filtering ---
    if ai_detected_category: category = ai_detected_category
    elif category_slug: category = get_object_or_404(Category, slug=category_slug)
    if category: products = products.filter(categories=category)

    # Calculate available_features based on resolved category (needed for _apply_all_query_filters)
    available_features = [] # Initialize here
    if category:
        schemas = load_category_schemas()
        target_schema = next((s for k, s in schemas.items() if k.lower() in category.name.lower()), None)
        if target_schema:
            available_features = target_schema.get('attributes', [])

    # Calculate all available brightness values for display in the filter panel
    all_available_brightness_values = sorted(list(set(
        ProductVariant.objects.filter(product__in=products).values_list('brightness', flat=True)
    )))
    # Filter out None and empty strings, and lowercase for consistency
    all_available_brightness_values = [
        b.lower() for b in all_available_brightness_values if b and b.strip()
    ]
    
    if search_queries:
        context_cat_name = None
        if category_slug:
             try:
                 context_cat_name = Category.objects.get(slug=category_slug).name
             except Category.DoesNotExist:
                 pass
        
        merged_filters = {}
        merged_colors = set()
        last_detected_category = None
        current_context = context_cat_name
        last_suggestion = None
        current_active_filters = {} # Replaced locked_features

        # Snapshots for filter states before current query (for conflict modal)
        prev_merged_filters = {}
        prev_merged_colors = set()
        prev_selected_features = {}
        prev_merged_negative_filters = {}
        prev_merged_negative_colors = set()
        prev_all_brightness_values = []

        for i, query in enumerate(search_queries):
             search_result = process_search_query(query, current_context)
             found_cat = search_result.get('category')
             found_filters = search_result.get('filters', {})
             normalized_filters = {k: normalize_filter_value(v) for k, v in found_filters.items()}
             found_colors = search_result.get('colors', [])
             found_neg_filters = search_result.get('negative_filters', {})
             normalized_neg_filters = {k: normalize_filter_value(v) for k, v in found_neg_filters.items()}
             found_neg_colors = search_result.get('negative_colors', [])
             found_suggestion = search_result.get('suggestion')
             found_attribute_suggestions = search_result.get('attribute_suggestions', {})
             
             # Conflict Check logic
             if found_cat and current_context and found_cat.lower() != current_context.lower() and i == len(search_queries) - 1:
                context_data = {
                     'products': [], # No products visible in background, as per user's request for "no backend filtering"
                     'selected_category': category, 'search_queries': search_queries,
                     'query_contributions': query_contributions, 'conflict_data': {'from': current_context, 'to': found_cat, 'trigger': query},
                     'attribute_suggestions': merged_attribute_suggestions,
                }
                if request.htmx:
                     grid_html = render_to_string('store/partials/product_grid.html', context_data, request=request)
                     modal_html = render_to_string('store/partials/conflict_modal.html', context_data, request=request)
                     return HttpResponse(grid_html + modal_html)
                return render(request, 'store/product_list.html', context_data)
            
             if found_cat:
                 last_detected_category = found_cat
                 current_context = found_cat
             if found_suggestion:
                 last_suggestion = found_suggestion

             is_contradictory = False
             contradiction_msg = ""

             # Contradiction Check 1: Current positive filters against active filters
             for k, v_list in normalized_filters.items():
                 current_val = v_list[0] if isinstance(v_list, list) and v_list else v_list # Ensure single value
                 if k in current_active_filters and current_active_filters[k] != current_val:
                     is_contradictory = True
                     contradiction_msg = f"Contradicts previous filter for '{k.replace('_', ' ')}'"
                     break
             
             # Contradiction Check 2: Current negative filters against active filters
             if not is_contradictory:
                for k, v_list in normalized_neg_filters.items():
                    current_val = v_list[0] if isinstance(v_list, list) and v_list else v_list # Ensure single value
                    effective_val_from_neg_filter = not current_val # e.g., 'without belt' (has_belt: True) means effective False
                    if k in current_active_filters and current_active_filters[k] != effective_val_from_neg_filter:
                        is_contradictory = True
                        contradiction_msg = f"Contradicts previous filter for '{k.replace('_', ' ')}'"
                        break

             # Contradiction Check 3: Positive vs Negative within the same query
             if not is_contradictory:
                for k, v_list in normalized_filters.items():
                    current_val = v_list[0] if isinstance(v_list, list) and v_list else v_list
                    if k in normalized_neg_filters:
                        neg_v_list = normalized_neg_filters[k]
                        neg_val = neg_v_list[0] if isinstance(neg_v_list, list) and neg_v_list else neg_v_list
                        if current_val != (not neg_val):
                            is_contradictory = True
                            contradiction_msg = f"Contradicts within this query for '{k.replace('_', ' ')}'"
                            break

             # Query Contribution & Merging logic
             query_contributions.append({
                 'query': query, 'category': found_cat if (i == 0 or not current_context or found_cat.lower() != current_context.lower()) else None,
                 'filters': normalized_filters if not is_contradictory else {},
                 'colors': found_colors if not is_contradictory else [],
                 'negative_filters': normalized_neg_filters if not is_contradictory else {},
                 'negative_colors': found_neg_colors, 'suggestion': found_suggestion,
                 'is_empty': not (found_cat or normalized_filters or found_colors or normalized_neg_filters or found_neg_colors),
                 'is_contradictory': is_contradictory, 'contradiction_msg': contradiction_msg
             })
             if not is_contradictory:
                 for k, v in normalized_filters.items():
                     if k not in merged_filters: merged_filters[k] = []
                     val_list = v if isinstance(v, list) else [v]
                     for val in val_list:
                         if val not in merged_filters[k]: merged_filters[k].append(val)
                     # Update current_active_filters for positive filters
                     current_active_filters[k] = val_list[0]
                 for c in found_colors: merged_colors.add(c)
                 
                 for k, v in normalized_neg_filters.items():
                     if k not in merged_negative_filters: merged_negative_filters[k] = []
                     val_list = v if isinstance(v, list) else [v]
                     for val in val_list:
                         if val not in merged_negative_filters[k]: merged_negative_filters[k].append(val)
                     # Update current_active_filters for negative filters
                     current_active_filters[k] = not val_list[0] # Effective False for positive val_list[0]
                 for c in found_neg_colors: merged_negative_colors.add(c)
                 merged_attribute_suggestions.update(found_attribute_suggestions)

        # UI Summary & Redirect Logic (remains the same)
        if last_detected_category: ai_search_summary['category'] = last_detected_category
        if last_suggestion: ai_search_summary['suggestion'] = last_suggestion

        # If a suggestion was just accepted, suppress it in the next response
        if request.GET.get('accepted_suggestion') == 'true':
            ai_search_summary['suggestion'] = None # Suppress suggestion
        
        # ... (rest of summary population) ...
        ai_filters = merged_filters
        ai_colors = list(merged_colors)
        if last_detected_category:
            ai_detected_category = Category.objects.filter(name__iexact=last_detected_category).first()
            if ai_detected_category and (not category_slug or ai_detected_category.slug != category_slug):
                base_url = reverse('product_list_by_category', args=[ai_detected_category.slug])
                params = request.GET.copy()
                params.setlist('q', search_queries)
                return redirect(f"{base_url}?{params.urlencode()}")

    # --- Category Resolution & Filtering ---
    if ai_detected_category: category = ai_detected_category
    elif category_slug: category = get_object_or_404(Category, slug=category_slug)
    if category: products = products.filter(categories=category)

    # Calculate all available brightness values for display in the filter panel
    all_available_brightness_values = sorted(list(set(
        ProductVariant.objects.filter(product__in=products).values_list('brightness', flat=True)
    )))
    # Filter out None and empty strings, and lowercase for consistency
    all_available_brightness_values = [
        b.lower() for b in all_available_brightness_values if b and b.strip()
    ]


    # --- Dynamic Feature & Brightness Filtering ---
    available_features = []
    selected_features = {} 
    all_brightness_values = []
    if category:
        schemas = load_category_schemas()
        target_schema = next((s for k, s in schemas.items() if k.lower() in category.name.lower()), None)

        if target_schema:
            available_features = target_schema.get('attributes', [])
            
            for attr in available_features:
                key = attr['key']
                
                ai_feature_values = ai_filters.get(key, [])
                manual_values = request.GET.getlist(f'feat_{key}')
                
                # Combine manual and AI values
                # Ensure all values are consistently handled (e.g., converted to lowercase strings for comparisons)
                combined_values = []
                for val in ai_feature_values + manual_values:
                    if isinstance(val, bool):
                        combined_values.append(val)
                    elif isinstance(val, str):
                        cleaned_val = val.strip().lower()
                        if cleaned_val == 'true':
                            combined_values.append(True)
                        elif cleaned_val == 'false':
                            combined_values.append(False)
                        elif cleaned_val: # Append other non-empty, non-boolean strings
                            combined_values.append(cleaned_val)
                
                # Remove duplicates while preserving order (optional, but good for cleanliness)
                final_selected_values = list(dict.fromkeys(combined_values))
                
                attr['selected_values'] = final_selected_values
                if final_selected_values:
                    selected_features[key] = final_selected_values

            # The all_brightness_values part for variant filtering.
            ai_brightness_values = ai_filters.get('brightness', [])
            manual_brightness_values = request.GET.getlist('feat_brightness') # this is still needed for side panel
            
            # Ensure all_brightness_values correctly includes both AI and manual sources
            all_brightness_values = list(set([str(v).lower() for v in ai_brightness_values + manual_brightness_values if str(v).strip()]))

    # After populating selected_features with positive filters,
    # now overlay negative filters for UI display where applicable.
    if merged_negative_filters and target_schema:
        for feature_key, feature_values_to_exclude in merged_negative_filters.items():
            feature_attr_def = next((attr for attr in available_features if attr['key'] == feature_key), None)
            if feature_attr_def and feature_attr_def.get('type') == 'boolean':
                # If we are negatively filtering for 'true' (e.g., 'without belt' -> exclude products where has_belt is true)
                # then for UI display, we should show 'False' as selected for that feature.
                if True in feature_values_to_exclude: # Assuming AI returns [True] for 'without X'
                    selected_features[feature_key] = [False]
                    # Also update attr['selected_values'] for direct template use within the loop
                    for attr in available_features:
                        if attr['key'] == feature_key:
                            attr['selected_values'] = [False]
                            break
                elif False in feature_values_to_exclude: # If we are negatively filtering for 'false'
                    selected_features[feature_key] = [True]
                    for attr in available_features:
                        if attr['key'] == feature_key:
                            attr['selected_values'] = [True]
                            break
    



    # --- Side Panel Price, Color, Size Filtering ---
    if min_price := request.GET.get('min_price'): products = products.filter(price__gte=min_price)
    if max_price := request.GET.get('max_price'): products = products.filter(price__lte=max_price)


    all_colors_from_db = sorted(list(set(ProductVariant.objects.values_list('color', flat=True))))
    all_colors = [c.capitalize() for c in all_colors_from_db] # Capitalize for display

    manual_colors_raw = request.GET.getlist('colors')
    manual_colors = [c.lower() for c in manual_colors_raw] # Normalize manual colors to lowercase

    # ai_colors should already be lowercased from ai_utils.py
    combined_colors = list(set(manual_colors + ai_colors))
    # ... (color normalization and negative color logic is the same) ...

    selected_sizes = request.GET.getlist('sizes')

    # --- REFACTORED Filtering on Variants ---
    if combined_colors and all_brightness_values:
        products = products.annotate(lower_color=Lower('variants__color')).filter(
            lower_color__in=combined_colors,
            variants__brightness__in=all_brightness_values
        ).distinct()
    elif combined_colors:
        products = products.annotate(lower_color=Lower('variants__color')).filter(lower_color__in=combined_colors).distinct()
    elif all_brightness_values:
        products = products.filter(variants__brightness__in=all_brightness_values).distinct()

    if selected_sizes:
        products = products.filter(variants__size__in=selected_sizes).distinct()

    # Apply AI Feature Filters (if any)
    for feature_key, feature_values in selected_features.items():
        if not feature_values: # Skip if no values selected for this feature
            continue
        
        # Find the feature definition from available_features to determine its type
        feature_attr_def = next((attr for attr in available_features if attr['key'] == feature_key), None)

        if feature_attr_def:
            if feature_attr_def.get('type') == 'boolean':
                for val in feature_values: # val will now be a Python boolean (True/False)
                    products = products.filter(features__contains={feature_key: val})
            elif feature_attr_def.get('type') == 'select':
                # Select features: filter for any of the selected options
                # Use case-insensitive matching for strings.
                q_objects = Q()
                for val in feature_values:
                    if isinstance(val, str):
                        lookup = f"features__{feature_key}__iexact"
                        q_objects |= Q(**{lookup: val})
                    else:
                        q_objects |= Q(features__contains={feature_key: val})
                products = products.filter(q_objects)
            elif feature_attr_def.get('type') == 'string': # Assuming string for now, similar to select
                q_objects = Q()
                for val in feature_values:
                    if isinstance(val, str):
                        lookup = f"features__{feature_key}__iexact"
                        q_objects |= Q(**{lookup: val})
                    else:
                        q_objects |= Q(features__contains={feature_key: val})
                products = products.filter(q_objects)
    


    # Apply negative AI Feature Filters
    for feature_key, feature_values in merged_negative_filters.items():
        if not feature_values:
            continue
        
        feature_attr_def = next((attr for attr in available_features if attr['key'] == feature_key), None)
        
        if feature_attr_def:
            if feature_attr_def.get('type') == 'boolean':
                # For boolean negative filters, if "true" is in values, exclude products where feature is true.
                # If "false" is in values, exclude products where feature is false.
                for val in feature_values: # val can be a bool (from AI) or str (from GET, if any)
                    if isinstance(val, bool):
                        products = products.exclude(features__contains={feature_key: val})
                    elif isinstance(val, str): # Handle string "true" or "false" (less likely for negative filters, but defensive)
                        if val.lower() == 'true':
                            products = products.exclude(features__contains={feature_key: True})
                        elif val.lower() == 'false':
                            products = products.exclude(features__contains={feature_key: False})
            elif feature_attr_def.get('type') in ['select', 'string']:
                # For select/string negative filters, exclude products that contain any of the negative values
                q_objects = Q()
                for val in feature_values: # val can be a bool (from AI) or str (from GET)
                    if isinstance(val, str):
                        q_objects |= Q(features__contains={feature_key: val.lower()}) # Ensure lowercased string
                    else: # Assume it's a non-string value, use as is (e.g., bool from AI output)
                        q_objects |= Q(features__contains={feature_key: val})
                products = products.exclude(q_objects)
    
    # Exclude products with variants matching negative colors
    if merged_negative_colors:
        products = products.exclude(variants__color__in=list(merged_negative_colors)).distinct()
    


    # --- Image Logic ---
    # Convert to list *after* all filtering is done
    products_list = list(products)
    products_list = _assign_display_images(products_list, combined_colors, all_brightness_values)

    all_sizes = sorted(list(set(ProductVariant.objects.values_list('size', flat=True))))

    # --- Final Context & Rendering ---
    context = {
        'products': products_list,
        'selected_category': category,
        'all_colors': all_colors,
        'all_sizes': all_sizes,
        'all_available_brightness_values': all_available_brightness_values,
        'selected_colors': combined_colors,
        'selected_sizes': selected_sizes,
        'selected_brightness': all_brightness_values,
        'available_features': available_features,
        'selected_features': selected_features,
        'ai_search_summary': ai_search_summary,
        'search_queries': search_queries,
        'query_contributions': query_contributions,
        'attribute_suggestions': merged_attribute_suggestions,
    }

    if request.htmx:
        # Render all components that need to be updated, including OOB swaps
        grid_html = render_to_string('store/partials/product_grid.html', context, request=request)
        filter_html = render_to_string('store/partials/oob_filter_sidebar.html', context, request=request)
        search_input_html = render_to_string('store/partials/search_input_area.html', context, request=request)
        page_header_html = render_to_string('store/partials/page_header.html', context, request=request)
        category_sidebar_html = render_to_string('store/partials/category_sidebar.html', context, request=request)
        smart_suggestion_html = render_to_string('store/partials/smart_suggestion_alert.html', context, request=request)
        
        # Combine all HTML parts for the response
        html = grid_html + filter_html + search_input_html + page_header_html + category_sidebar_html + smart_suggestion_html
        response = HttpResponse(html)
        response['HX-Push-Url'] = request.get_full_path()
        return response

    return render(request, 'store/product_list.html', context)


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.prefetch_related('variants__images'), slug=slug)
    
    # Get all variants in stock
    all_in_stock_variants = product.variants.filter(stock_quantity__gt=0).order_by('color', 'size', 'brightness')

    if not all_in_stock_variants.exists():
        context = {'product': product, 'no_stock_at_all': True}
        return render(request, 'store/product_detail.html', context)

    # Determine currently selected color, brightness, size from URL GET parameters (if any)
    selected_color_param = request.GET.get('color')
    selected_brightness_param = request.GET.get('brightness') # For context/display
    selected_size_param = request.GET.get('size') # For context/display

    # Attempt to find variant based on URL parameters
    initial_selected_variant = None
    
    if selected_color_param and selected_size_param:
        # Try to match both color and size
        initial_selected_variant = all_in_stock_variants.filter(
            color__iexact=selected_color_param,
            size__iexact=selected_size_param
        ).first()
    
    if not initial_selected_variant and selected_color_param:
        # Fallback: match just the color and pick the first size
        initial_selected_variant = all_in_stock_variants.filter(
            color__iexact=selected_color_param
        ).first()

    # If no variant found or no params provided, take the first available
    if not initial_selected_variant:
        initial_selected_variant = all_in_stock_variants.first()

    # Now, use the attributes of the found initial_selected_variant for the context
    selected_color = initial_selected_variant.color
    selected_brightness = initial_selected_variant.brightness
    selected_size = initial_selected_variant.size

    # The currently chosen variant for rendering the detail page is simply the initial_selected_variant
    current_selected_variant = initial_selected_variant

    images = current_selected_variant.images.all() if current_selected_variant else []

    context = {
        'product': product,
        'selected_variant': current_selected_variant,
        'images': images,
        'available_colors_overall': sorted(list(set(v.color for v in all_in_stock_variants))),
        'available_sizes_for_selected_color': sorted(list(set(
            v.size for v in all_in_stock_variants.filter(color=selected_color)
        ))),
        'available_brightness_for_selected_color': sorted(list(set(
            v.brightness for v in all_in_stock_variants.filter(color=selected_color) if v.brightness
        ))),
        'selected_color': selected_color,
        'selected_size': selected_size,
        'selected_brightness': selected_brightness, # This value is from initial_selected_variant.brightness. The param value is just for initial search.
    }
    
    return render(request, 'store/product_detail.html', context)


def add_to_cart(request, variant_id):
    cart = Cart(request)
    cart.add(variant_id)
    return render(request, 'store/partials/menu_cart.html', {'cart': cart})

def add_to_cart_form(request):
    variant_id = request.POST.get('variant_id')
    cart = Cart(request)
    if variant_id:
        cart.add(variant_id)
    return render(request, 'store/partials/menu_cart.html', {'cart': cart})

def clear_cart(request):
    cart = Cart(request)
    if 'cart' in request.session:
        del request.session['cart']
        request.session.modified = True
    return redirect('product_list')

def cart_detail(request):
    cart = Cart(request)
    return render(request, 'store/cart_detail.html', {'cart': cart})

def _get_matching_products(items_data):
    example_products_output = []
    MAX_PRODUCTS_PER_ITEM = 5 
    
    seen_product_ids = set()

    for item in items_data:
        product_filters = Q()
        variant_filters = Q()
        
        if item.get('category'):
            product_filters &= Q(categories__name__iexact=item['category'])
        
        if item.get('color'):
            variant_filters &= Q(color__iexact=item['color'])

        if item.get('features'):
            for feature_key, feature_value in item['features'].items():
                # Handle list or single value
                raw_value = feature_value[0] if isinstance(feature_value, list) else feature_value
                value_to_match = normalize_filter_value(raw_value)
                product_filters &= Q(features__contains={feature_key: value_to_match})

        matching_products_queryset = Product.objects.filter(product_filters).prefetch_related('variants__images')
        if variant_filters:
            matching_products_queryset = matching_products_queryset.filter(variants__in=ProductVariant.objects.filter(variant_filters))
        
        # Exclude already seen products
        matching_products_queryset = matching_products_queryset.exclude(id__in=seen_product_ids).distinct().order_by('?')[:MAX_PRODUCTS_PER_ITEM]

        # Assign display images
        products_with_display_images = _assign_display_images(
            list(matching_products_queryset),
            [item['color'].lower()] if item.get('color') else [],
            []
        )

        category_products = []
        for p in products_with_display_images:
            seen_product_ids.add(p.id)
            
            images_to_show = []
            if p.display_variant:
                all_v_images = list(p.display_variant.images.all())
                # Ensure main is first if it exists
                if p.display_image and p.display_image in all_v_images:
                     all_v_images.remove(p.display_image)
                     all_v_images.insert(0, p.display_image)
                
                images_to_show = all_v_images[:2]
            
            # If no variant images, try product images fallback? 
            # (Usually covered by _assign_display_images fallback logic which finds a variant)
            
            for img in images_to_show:
                 category_products.append({
                    'product_name': p.name,
                    'product_slug': p.slug,
                    'image_url': img.image.url
                })

        # Always append, even if empty, to maintain index parity with input items
        example_products_output.append({
            'category': item.get('category', 'Unknown'),
            'products': category_products
        })

    return example_products_output


def visual_search(request):
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == 'identify_items':
            if request.FILES.get('image'):
                image_file = request.FILES['image']
                user_prompt = request.POST.get('prompt')
                box_str = request.POST.get('box')
                items = api_identify_items(image_file, box=box_str, user_context=user_prompt)
                
                # Use helper
                example_products_output = _get_matching_products(items)

                return JsonResponse({'items': items, 'example_products': example_products_output})
            else:
                 # Should probably return error if image missing for identify_items
                 return JsonResponse({'error': 'Image required'}, status=400)

        elif action == 'filter_examples':
            try:
                items_data = json.loads(request.POST.get('items_data', '[]'))
                examples = _get_matching_products(items_data)
                return JsonResponse({'example_products': examples})
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)

        
        # Default: Detect People (Action not specified or implies detect people)
        if request.FILES.get('image'):
             image_file = request.FILES['image']
             user_prompt = request.POST.get('prompt')
             people = api_detect_people(image_file, user_context=user_prompt)
             return JsonResponse({'people': people})
        
    return render(request, 'store/visual_search/index.html')
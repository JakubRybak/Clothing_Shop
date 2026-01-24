import os
import json
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google.oauth2 import service_account
from django.conf import settings
from django.core.cache import cache
from .models import Product, ProductImage, ProductVariant

# Load credentials and project settings
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "advanced-searching-pdf")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")

# If on local machine with a key file, use it. Otherwise, use default (Cloud Run)
CREDENTIALS_PATH = os.path.join(settings.BASE_DIR, 'gcp_key.json')
if os.path.exists(CREDENTIALS_PATH):
    credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
    vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)
else:
    # On Cloud Run, it uses the service's own identity automatically
    vertexai.init(project=PROJECT_ID, location=LOCATION)

def load_category_schemas():
    """Loads category schemas from a JSON file."""
    schema_path = os.path.join(settings.BASE_DIR, 'store', 'schemas.json')
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading schemas from {schema_path}: {e}")
        return {}

CATEGORY_SCHEMAS = load_category_schemas()

def generate_product_features(product_id):
    """
    Generates features for a product using Vertex AI Gemini, based on its text
    and a sample of images from its variants.
    """
    try:
        product = Product.objects.prefetch_related('variants__images').get(id=product_id)
        target_schema = None
        schema_name = None
        categories = list(product.categories.all())

        for category in categories:
            for key, schema in CATEGORY_SCHEMAS.items():
                if key.lower() in category.name.lower():
                    target_schema = schema
                    schema_name = key
                    break
            if target_schema:
                break
        
        if not target_schema:
            print(f"DEBUG: No schema for {product.name}")
            return

        # --- Image Selection (New Logic) ---
        images_to_send = []
        all_variant_images = []
        for variant in product.variants.all():
            all_variant_images.extend(list(variant.images.all()))

        # Prioritize main images, then add others, up to 5 total
        main_images = [img for img in all_variant_images if img.is_main][:5]
        images_to_send.extend(main_images)
        if len(images_to_send) < 5:
            other_images = [img for img in all_variant_images if not img.is_main][:5 - len(images_to_send)]
            images_to_send.extend(other_images)
            
        if not images_to_send:
            print(f"DEBUG: No images found for product {product.name} to generate features.")
            return

        image_parts = []
        for img_obj in images_to_send:
            mime_type = "image/png" if img_obj.image.path.lower().endswith('.png') else "image/jpeg"
            with open(img_obj.image.path, "rb") as f:
                image_parts.append(Part.from_data(data=f.read(), mime_type=mime_type))
        
        prompt_text = f"Analyze product: '{product.name}' (Category: {schema_name}).\n"
        if product.description: prompt_text += f"Desc: {product.description}\n"
        
        prompt_structure = {}
        for attr in target_schema['attributes']:
            prompt_structure[attr['key']] = f"{attr['type']}. {attr['question']}"
            if 'options' in attr: prompt_structure[attr['key']] += f" Options: {attr['options']}"
        prompt_text += f"Return JSON strictly matching schema:\n{json.dumps(prompt_structure)}"

        model = GenerativeModel("gemini-2.0-flash-lite-001")
        response = model.generate_content([prompt_text] + image_parts, generation_config={"response_mime_type": "application/json"})
        
        text = response.text.strip().replace("```json", "").replace("```", "")
        
        raw_features = json.loads(text)
        
        # Normalize string values in features to lowercase for consistent filtering
        normalized_features = {}
        for k, v in raw_features.items():
            if isinstance(v, str):
                normalized_features[k] = v.lower()
            else:
                normalized_features[k] = v
        
        product.features = normalized_features
        product.save(update_fields=['features'])
        print(f"Generated features for {product.name}")
        
    except Exception as e:
        print(f"Error generating features: {e}")

def process_search_query(user_query, current_category_name=None):
    """
    Process natural language search query using a hybrid approach:
    1. Redis (Cache)
    2. PostgreSQL (Permanent History)
    3. Gemini AI (Fresh generation)
    """
    from .models import SearchQuery  # Import here to avoid circular dependencies

    try:
        query_normalized = user_query.strip().lower()
        
        # --- 1. REDIS CACHE LAYER ---
        cache_key = f"search_ai_v2_{query_normalized}_{current_category_name}".replace(" ", "_").lower()
        cached_result = cache.get(cache_key)
        if cached_result:
            print(f"DEBUG: Redis HIT for '{query_normalized}'")
            return cached_result
            
        # --- 2. POSTGRESQL LAYER ---
        db_query = SearchQuery.objects.filter(query_text=query_normalized).first()
        if db_query:
            print(f"DEBUG: PostgreSQL HIT for '{query_normalized}'")
            db_query.count += 1
            db_query.save(update_fields=['count'])
            
            # Save back to Redis for next time
            cache.set(cache_key, db_query.result_data, timeout=86400)
            return db_query.result_data

        print(f"DEBUG: Cache/DB MISS for '{query_normalized}' - Calling Gemini...")
        
        schemas = load_category_schemas()
        
        # Get all unique colors from ProductVariant for LLM guidance
        available_product_colors = sorted(list(set(ProductVariant.objects.values_list('color', flat=True))))
        # Normalize to lowercase for consistency
        available_product_colors_lower = [c.lower() for c in available_product_colors]
        
        # --- Step 1: Category Detection ---
        target_category = None
        
        if not target_category:
            prompt = f"Classify query '{user_query}' into one of: {list(schemas.keys())}. Return ONLY category name or 'Unknown'."
            # If we have a context, we can add it, but strictly as context, not a constraint.
            if current_category_name:
                prompt += f"\nContext: User is currently viewing '{current_category_name}' category. "
                prompt += "Instructions for Context:\n"
                prompt += "1. IF the query is a synonym or exact match for a DIFFERENT category (e.g. 'coat', 'trousers'), you MUST return that new category.\n"
                prompt += f"2. ONLY keep '{current_category_name}' if the query describes a FEATURE, COLOR, or STYLE (e.g. 'black', 'leather', 'belt') of {current_category_name}.\n"
                prompt += "3. If the query implies an item that completely contradicts the current category, switch."
            
            model = GenerativeModel("gemini-2.0-flash-lite-001")
            resp = model.generate_content(prompt)
            predicted = resp.text.strip().replace("'", "").replace('"', "")
            
            print(f"DEBUG: Category prediction for '{user_query}': {predicted}")
            
            for cat in schemas.keys():
                # Check exact match or plural "s" removal match
                if cat.lower() == predicted.lower() or cat.lower() == predicted.lower().rstrip('s'):
                    target_category = cat
                    break
        
        print(f"DEBUG: Resolved Target Category: {target_category}")
        
        # Fallback: If AI couldn't classify (Unknown) but we have a context (e.g. user is in "Coats" searching "black"),
        # assume the user implies the current category.
        if not target_category and current_category_name:
            print(f"DEBUG: Fallback to context category '{current_category_name}' for query '{user_query}'")
            # Verify the context category actually exists in our schemas to avoid crashes
            for key in schemas.keys():
                if key.lower() == current_category_name.lower():
                    target_category = key
                    break
        
        result = {"category": target_category, "filters": {}, "colors": [], "negative_filters": {}, "negative_colors": []}
        if not target_category:
            return result

        # --- Step 2: Direct Feature Extraction (One Shot) ---
        # Instead of embedding, we give the LLM the specific schema for the detected category
        # and ask it to pick relevant fields.
        
        target_schema = schemas.get(target_category)

        if not target_schema:
            print(f"DEBUG: Category '{target_category}' not found in schemas. Available: {list(schemas.keys())}")
            return result
        
        # Simplify schema for prompt (remove potentially confusing types if not needed, but options help context)
        # We want: key, question, options
        prompt_schema = []
        for attr in target_schema.get('attributes', []):
            item = f"Feature '{attr['key']}': {attr['question']}"
            if 'options' in attr:
                item += f" (Options: {', '.join(attr['options'])})"
            prompt_schema.append(item)
        
        # Dynamically add brightness to prompt_schema
        brightness_choices = [choice[0] for choice in ProductVariant.BRIGHTNESS_CHOICES]
        prompt_schema.append(f"Feature 'brightness': select. What is the overall brightness of the product's color? (Options: {', '.join(brightness_choices)})")

        prompt = f"Analyze search query: '{user_query}'\n"
        prompt += f"Context: User is searching in category '{target_category}'.\n"
        prompt += f"Available Colors: {', '.join(available_product_colors)}. Prioritize these.\n\n"
        prompt += "Available Features:\n" + "\n".join(prompt_schema) + "\n\n"
        
        prompt += " Instructions:\n"
        prompt += "1. Identify features from the list (including 'brightness') that are EXPLICITLY mentioned or VERY STRONGLY implied by the query.\n"
        prompt += "2. **CRITICAL COLOR DETECTION**: If a term is an exact match for a color in 'Available Colors', extract it ONLY as a color. DO NOT infer brightness or color_pattern from these exact color matches.\n"
        prompt += "3. Extract values for identified features. Use exact option names (e.g., 'dark' for 'brightness').\n"
        prompt += "4. **AVOID INFERENCE**: DO NOT infer 'brightness' or 'color_pattern' unless EXPLICITLY mentioned or very strongly implied, and only if no direct color match was found (e.g., 'dark coat' implies brightness:dark, but 'black coat' implies color:black, NOT brightness:dark or color_pattern:solid).\n"
        prompt += "5. EXCLUSIONS (Negative Logic): If the query explicitly uses NEGATIVE language (e.g., 'not', 'no', 'without', 'except'), extract those features into `negative_filters` and `negative_colors`.\n"
        prompt += "   - Example: 'not red' -> negative_colors: ['red'] (always lowercase)\n"
        prompt += "   - Example: 'no zipper' -> negative_filters: {'has_zipper': true}\n"
        prompt += "6. SUGGESTIONS: If the query is VAGUE or implies a specific need without technical detail, suggest ONE attribute from the schema. \n"
        prompt += "7. Return JSON: \n"
        prompt += "   { \n"
        prompt += "     \"filters\": {\"feature_key\": [\"value\"]}, \n"
        prompt += "     \"colors\": [...], \n"
        prompt += "     \"negative_filters\": {\"feature_key\": [\"value_to_exclude\"]}, \n"
        prompt += "     \"negative_colors\": [\"Color_to_exclude\"], \n"
        prompt += "     \"suggestion\": {\"text\": \"...\", \"suggested_query\": \"...\"} \n"
        prompt += "   }\n"
        prompt += "8. IMPORTANT: If a feature is NOT mentioned, DO NOT include it in the output. Do NOT return 'unknown'.\n"
        
        model = GenerativeModel("gemini-2.0-flash-lite-001")
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.endswith("```"): text = text[:-3]
        
        data = json.loads(text)
        
        raw_filters = data.get("filters", {})
        
        # Post-processing: If brightness is detected, clear implied colors
        if 'brightness' in raw_filters:
            # Ensure it's a list even if Gemini returned a single string for brightness
            brightness_values = raw_filters.get('brightness')
            if not isinstance(brightness_values, list):
                brightness_values = [brightness_values]
            
            # Check if any detected brightness value matches 'dark', 'medium', or 'light'
            # If so, it means the query was primarily about brightness, not specific colors
            if any(b.lower() in ['dark', 'medium', 'light'] for b in brightness_values if isinstance(b, str)):
                data['colors'] = [] # Clear colors if brightness is explicitly set AND it's a brightness term

        # Ensure colors are lowercased when extracted
        result["colors"] = [c.lower() for c in data.get("colors", [])]
        result["negative_colors"] = [c.lower() for c in data.get("negative_colors", [])]
        result["suggestion"] = data.get("suggestion") # Extract suggestion
        
        # --- Post-Processing: Flatten filters ---
        def flatten_filters(raw_data):
            cleaned = {}
            if target_category in raw_data and isinstance(raw_data[target_category], dict):
                 cleaned = raw_data[target_category]
            else:
                 cleaned = raw_data
                 
            final = {}
            for k, v in cleaned.items():
                clean_key = k.split(".")[-1]
                values = v if isinstance(v, list) else [v]
                valid_values = []
                for val in values:
                    # All extracted colors should already be lowercased from above
                    val_str = str(val).lower().strip()
                    if val_str == 'unknown' or val_str == '': continue
                    if val_str == 'other' and is_generic_query: continue
                    valid_values.append(val)
                if valid_values:
                    final[clean_key] = valid_values
            return final

        # Generic terms blackhole
        GENERIC_TERMS = ["pants", "trousers", "slacks", "bottoms", "coat", "coats", "jacket", "jackets", "outerwear", "shirt", "shirts", "tshirt", "t-shirt", "tops", "wear", "clothes", "clothing"]
        is_generic_query = user_query.lower().strip() in GENERIC_TERMS
        
        result["filters"] = flatten_filters(data.get("filters", {}))
        result["negative_filters"] = flatten_filters(data.get("negative_filters", {}))
        
        print(f"DEBUG: '{user_query}' -> extracted: {result}")
        
        # --- 4. SAVE TO PERSISTENT STORAGE & CACHE ---
        # Save to PostgreSQL
        SearchQuery.objects.update_or_create(
            query_text=query_normalized,
            defaults={
                'category_name': target_category,
                'result_data': result
            }
        )
        
        # Cache the successful result in Redis
        cache.set(cache_key, result, timeout=86400) # Cache for 24 hours
        
        return result

    except Exception as e:
        print(f"Error processing search: {e}")
        return {}

def generate_brightness_for_variant(variant_id):
    """
    Detects and saves brightness for a ProductVariant based on its main image.
    Returns (success: bool, message: str).
    """
    try:
        variant = ProductVariant.objects.get(id=variant_id)
        main_image = variant.images.filter(is_main=True).first()
        
        if not main_image:
            # Fallback to any image if no main image exists
            main_image = variant.images.first()

        if main_image:
            detected_brightness = api_detect_brightness(main_image)
            if detected_brightness:
                # Validate detected_brightness against BRIGHTNESS_CHOICES
                valid_choices = [choice[0] for choice in variant.BRIGHTNESS_CHOICES]
                if detected_brightness in valid_choices:
                    variant.brightness = detected_brightness
                    variant.save(update_fields=['brightness'])
                    return True, f"Detected brightness '{detected_brightness}' for variant {variant.id} ({variant.product.name} - {variant.color})."
                else:
                    return False, f"AI detected invalid brightness '{detected_brightness}' for variant {variant.id}. Must be one of {valid_choices}."
            else:
                return False, f"AI could not detect brightness for variant {variant.id}."
        else:
            return False, f"No images found for variant {variant.id}, cannot detect brightness."
            
    except Exception as e:
        return False, f"Error generating brightness for variant {variant_id}: {e}"


def api_detect_people(image_file, user_context=None):
    """
    Analyzes an image to find people.
    user_context: e.g. "Find the woman in the red dress"
    """
    try:
        image_file.seek(0)
        image_data = image_file.read()
        image_part = Part.from_data(data=image_data, mime_type=image_file.content_type)
        
        prompt = "Identify all distinct people in this image."
        if user_context:
            prompt += f" Context/Focus: {user_context}."
            
        prompt += """
        For EACH person, provide a bounding box [ymin, xmin, ymax, xmax] (normalized coordinates 0-1000).
        Return JSON:
        {
            "people": [
                {"id": 1, "box_2d": [ymin, xmin, ymax, xmax], "label": "Person 1"}
            ]
        }
        """
        
        model = GenerativeModel("gemini-2.0-flash-lite-001")
        response = model.generate_content([prompt, image_part], generation_config={"response_mime_type": "application/json"})
        
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.endswith("```"): text = text[:-3]
        
        return json.loads(text).get("people", [])
    except Exception as e:
        print(f"Error detecting people: {e}")
        return []

def api_identify_items(image_file, box=None, user_context=None):
    """
    Analyzes a person to find clothing items.
    """
    try:
        image_file.seek(0)
        image_data = image_file.read()
        image_part = Part.from_data(data=image_data, mime_type=image_file.content_type)
        
        # Load schemas to guide the AI on valid feature keys AND values
        schema_guidance = ""
        for cat, details in CATEGORY_SCHEMAS.items():
            schema_guidance += f"- {cat}:\n"
            for attr in details.get('attributes', []):
                options_str = ""
                if 'options' in attr:
                    options_str = f" (Options: {', '.join(attr['options'])})"
                schema_guidance += f"  * {attr['key']}{options_str}\n"

        prompt = "Analyze the clothing worn by the person in this image. "
        if box:
            prompt += f"Focus strictly on the person within bounding box: {box}. "
        if user_context:
            prompt += f"User specifically asked about: '{user_context}'. "

        prompt += f"""
        Identify visible clothing items. Map them to one of these categories: {list(CATEGORY_SCHEMAS.keys())}.
        
        CRITICAL: For the 'features' dictionary, you MUST use ONLY the allowed keys AND allowed option values listed below:
        {schema_guidance}
        
        Return JSON:
        {{
            "items": [
                {{
                    "name": "Display Name", 
                    "category": "ExactCategoryName", 
                    "color": "Primary Color",
                    "features": {{
                        "allowed_key_1": true,
                        "allowed_key_2": "exact_option_value"
                    }}
                }}
            ]
        }}
        """
        
        model = GenerativeModel("gemini-2.0-flash-lite-001")
        response = model.generate_content([prompt, image_part], generation_config={"response_mime_type": "application/json"})
        
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.endswith("```"): text = text[:-3]
        
        return json.loads(text).get("items", [])
    except Exception as e:
        print(f"Error identifying items: {e}")
        return []


def api_detect_brightness(product_image):
    """
    Analyzes a ProductImage to classify its brightness ('light', 'medium', 'dark').
    """
    try:
        # Ensure image file is at the beginning
        with open(product_image.image.path, "rb") as f:
            image_data = f.read()

        mime_type = "image/png"
        if product_image.image.path.lower().endswith(('.jpg', '.jpeg')):
            mime_type = "image/jpeg"
        
        image_part = Part.from_data(data=image_data, mime_type=mime_type)
        
        prompt = """
        Given this product image, classify the overall brightness of the main product's color as one of 'light', 'medium', or 'dark'.
        Return a single JSON object with one key 'brightness' and its corresponding value.
        Example: {"brightness": "dark"}
        """
        
        model = GenerativeModel("gemini-2.0-flash-lite-001")
        response = model.generate_content([prompt, image_part], generation_config={"response_mime_type": "application/json"})
        
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.endswith("```"): text = text[:-3]
        
        brightness_data = json.loads(text)
        return brightness_data.get("brightness")
    except Exception as e:
        print(f"Error detecting brightness for image {product_image.id}: {e}")
        return None
from django import template
from urllib.parse import urlencode

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Template filter to allow accessing dictionary values by a variable key.
    Usage: {{ my_dictionary|get_item:my_key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter(name='add_param')
def add_param(dictionary, key_value_str):
    """
    Adds a key-value pair to a dictionary. Expects 'key,value' string.
    Usage: {{ my_dict|add_param:'color,red' }}
    Returns a new dictionary with the item added.
    """
    new_dict = dictionary.copy()
    parts = key_value_str.split(',', 1)
    if len(parts) == 2:
        key, value = parts
        new_dict[key] = value
    elif len(parts) == 1: # Handle cases where value might be empty
        key = parts[0]
        new_dict[key] = '' # Or leave it as None, depending on desired behavior
    return new_dict


@register.filter(name='url_params')
def url_params(base_url, params_dict):
    """
    Appends URL parameters from a dictionary to a base URL.
    Example: "{{ '/products/'|url_params:my_dict }}"
    """
    if not isinstance(params_dict, dict):
        return base_url
    
    encoded_params = urlencode({k: v for k, v in params_dict.items() if v is not None and v != ''})
    if encoded_params:
        separator = '&' if '?' in base_url else '?'
        return f"{base_url}{separator}{encoded_params}"
    return base_url

@register.filter(name='format_label')
def format_label(value):
    if not value: return ""
    # Clean up common keys: 'style_category' -> 'Style', 'has_buttons' -> 'Has buttons'
    label = value.replace('_category', '').replace('has_', 'Has ').replace('is_', 'Is ')
    label = label.replace('_', ' ').strip()
    return f"{label[0].upper() + label[1:]}:"
# Full mapping of specific color names to broader color families for filtering
COLOR_MAPPING = {
    # Grey Family
    'anthracite': 'Grey', 'charcoal': 'Grey', 'dark grey': 'Grey', 'mid grey': 'Grey',
    'light grey': 'Grey', 'silver': 'Grey', 'slate': 'Grey', 'graphite': 'Grey',
    'ash': 'Grey', 'smoke': 'Grey', 'steel': 'Grey', 'gunmetal': 'Grey',

    # Green Family
    'olive': 'Green', 'light olive': 'Green', 'dark green': 'Green', 'dusty green': 'Green',
    'pale green': 'Green', 'brownish green': 'Green', 'teal green': 'Green', 
    'steel green': 'Green', 'yellow green': 'Green', 'emerald': 'Green', 'lime': 'Green',
    'sage': 'Green', 'mint': 'Green', 'forest green': 'Green', 'army green': 'Green',
    'khaki green': 'Green', 'moss': 'Green', 'fern': 'Green',

    # Blue Family
    'navy': 'Blue', 'light blue': 'Blue', 'pale blue': 'Blue', 'dark turquoise': 'Blue',
    'sky blue': 'Blue', 'teal': 'Blue', 'turquoise': 'Blue', 'indigo': 'Blue',
    'royal blue': 'Blue', 'baby blue': 'Blue', 'cyan': 'Blue', 'midnight blue': 'Blue',
    'denim': 'Blue', 'sapphire': 'Blue',

    # Red Family
    'burgundy': 'Red', 'carmine': 'Red', 'maroon': 'Red', 'crimson': 'Red',
    'scarlet': 'Red', 'brick red': 'Red', 'cherry': 'Red', 'wine': 'Red', 'ruby': 'Red',

    # Pink Family
    'pink': 'Pink', 'dusty rose': 'Pink', 'magenta': 'Pink', 'fuchsia': 'Pink',
    'rose': 'Pink', 'salmon': 'Pink', 'coral': 'Pink', 'hot pink': 'Pink',
    'blush': 'Pink', 'peach': 'Pink', 'pastel pink': 'Pastel pink',

    # Brown Family
    'brown': 'Brown', 'dark brown': 'Brown', 'dusty brown': 'Brown', 'golden brown': 'Brown',
    'coffee': 'Brown', 'copper': 'Brown', 'mahogany': 'Brown', 'taupe': 'Brown',
    'beige': 'Brown', 'tan': 'Brown', 'khaki': 'Brown', 'camel': 'Brown',
    'chocolate': 'Brown', 'sand': 'Brown', 'bronze': 'Brown', 'cocoa': 'Brown', 'cinnamon': 'Brown',

    # Purple Family
    'dark violet': 'Purple', 'steel violet': 'Purple', 'lavender': 'Purple',
    'lilac': 'Purple', 'violet': 'Purple', 'plum': 'Purple', 'mauve': 'Purple',
    'orchid': 'Purple', 'grape': 'Purple', 'aubergine': 'Purple',

    # Yellow/Orange Family
    'yellow': 'Yellow', 'gold': 'Yellow', 'mustard': 'Yellow', 'canary': 'Yellow',
    'lemon': 'Yellow', 'amber': 'Orange', 'orange': 'Orange', 'rust': 'Orange',
    'burnt orange': 'Orange', 'apricot': 'Orange', 'tangerine': 'Orange', 'light yellow': 'Light yellow',

    # White/Neutral Family
    'cream': 'White', 'nude': 'White', 'ivory': 'White', 'off-white': 'White',
    'eggshell': 'White', 'vanilla': 'White', 'snow': 'White', 'bone': 'White',

    # Black Family
    'black': 'Black', 'jet black': 'Black', 'onyx': 'Black', 'pitch black': 'Black',

    # New & Specific Mappings requested
    'aqua': 'Aqua',
    'blue jeans': 'Blue jeans',
    'dark grey jeans': 'Dark grey jeans',
    'golden': 'Golden',
    'hyacinth': 'Hyacinth',
    'wheat': 'Wheat',

    # Special
    'multicolor': 'Multicolor',
}

# The list of general color groups Gemini is forced to pick from
COLOR_GROUPS = [
    "Aqua", "Black", "Blue", "Blue jeans", "Brown", "Dark grey jeans", 
    "Golden", "Green", "Grey", "Hyacinth", "Light yellow", "Multicolor", 
    "Pastel pink", "Pink", "Purple", "Red", "Wheat", "White"
]

# Mapping for UI color squares (Hex/CSS values)
COLOR_HEX_MAPPING = {
    'Aqua': '#00FFFF',
    'Black': '#000000',
    'Blue': '#0000FF',
    'Blue jeans': '#5d8aa8',
    'Brown': '#8B4513',
    'Dark grey jeans': '#4a4e4d',
    'Golden': '#FFD700',
    'Green': '#008000',
    'Grey': '#808080',
    'Hyacinth': '#9370DB',
    'Light yellow': '#FFFFE0',
    'Multicolor': 'linear-gradient(to right, red, orange, yellow, green, blue, indigo, violet)',
    'Pastel pink': '#FFD1DC',
    'Pink': '#FFC0CB',
    'Purple': '#800080',
    'Red': '#FF0000',
    'Wheat': '#F5DEB3',
    'White': '#FFFFFF',
    'Orange': '#FFA500', # Fallback for mapping
}

def get_color_family(specific_color):
    if not specific_color: return "Unknown"
    clean_color = specific_color.lower().strip()
    return COLOR_MAPPING.get(clean_color, clean_color.capitalize())
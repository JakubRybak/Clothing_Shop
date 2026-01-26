# Full mapping of specific color names to broader color families for filtering
COLOR_MAPPING = {
    # Black Family
    'black': 'Black', 'jet black': 'Black', 'onyx': 'Black', 'pitch black': 'Black',

    # Blue Family
    'navy': 'Blue', 'light blue': 'Blue', 'pale blue': 'Blue', 'dark turquoise': 'Blue',
    'sky blue': 'Blue', 'teal': 'Blue', 'turquoise': 'Blue', 'indigo': 'Blue',
    'royal blue': 'Blue', 'baby blue': 'Blue', 'cyan': 'Blue', 'midnight blue': 'Blue',
    'denim': 'Blue', 'sapphire': 'Blue', 'aqua': 'Blue', 'blue jeans': 'Blue',
    'dark grey jeans': 'Blue', # As requested: all jeans map to Blue

    # Brown Family
    'brown': 'Brown', 'dark brown': 'Brown', 'dusty brown': 'Brown', 'golden brown': 'Brown',
    'coffee': 'Brown', 'copper': 'Brown', 'mahogany': 'Brown', 'taupe': 'Brown',
    'chocolate': 'Brown', 'bronze': 'Brown', 'cocoa': 'Brown', 
    'cinnamon': 'Brown',

    # Beige Family
    'beige': 'Beige', 'tan': 'Beige', 'khaki': 'Beige', 'camel': 'Beige',
    'sand': 'Beige', 'wheat': 'Beige', 'cream': 'Beige', 'nude': 'Beige', 
    'ivory': 'Beige', 'off-white': 'Beige', 'eggshell': 'Beige', 
    'vanilla': 'Beige', 'bone': 'Beige',

    # Green Family
    'olive': 'Green', 'light olive': 'Green', 'dark green': 'Green', 'dusty green': 'Green',
    'pale green': 'Green', 'brownish green': 'Green', 'teal green': 'Green', 
    'steel green': 'Green', 'yellow green': 'Green', 'emerald': 'Green', 'lime': 'Green',
    'sage': 'Green', 'mint': 'Green', 'forest green': 'Green', 'army green': 'Green',
    'khaki green': 'Green', 'moss': 'Green', 'fern': 'Green',

    # Grey Family
    'anthracite': 'Grey', 'charcoal': 'Grey', 'dark grey': 'Grey', 'mid grey': 'Grey',
    'light grey': 'Grey', 'silver': 'Grey', 'slate': 'Grey', 'graphite': 'Grey',
    'ash': 'Grey', 'smoke': 'Grey', 'steel': 'Grey', 'gunmetal': 'Grey',

    # Orange Family
    'orange': 'Orange', 'amber': 'Orange', 'rust': 'Orange', 'burnt orange': 'Orange', 
    'apricot': 'Orange', 'tangerine': 'Orange',

    # Pink Family
    'pink': 'Pink', 'dusty rose': 'Pink', 'magenta': 'Pink', 'fuchsia': 'Pink',
    'rose': 'Pink', 'salmon': 'Pink', 'coral': 'Pink', 'hot pink': 'Pink',
    'blush': 'Pink', 'peach': 'Pink', 'pastel pink': 'Pink',

    # Purple Family
    'purple': 'Purple', 'dark violet': 'Purple', 'steel violet': 'Purple', 'lavender': 'Purple',
    'lilac': 'Purple', 'violet': 'Purple', 'plum': 'Purple', 'mauve': 'Purple',
    'orchid': 'Purple', 'grape': 'Purple', 'aubergine': 'Purple', 'hyacinth': 'Purple',

    # Red Family
    'red': 'Red', 'burgundy': 'Red', 'carmine': 'Red', 'maroon': 'Red', 'crimson': 'Red',
    'scarlet': 'Red', 'brick red': 'Red', 'cherry': 'Red', 'wine': 'Red', 'ruby': 'Red',

    # White Family
    'white': 'White', 'snow': 'White',

    # Yellow Family
    'yellow': 'Yellow', 'gold': 'Yellow', 'mustard': 'Yellow', 'canary': 'Yellow',
    'lemon': 'Yellow', 'light yellow': 'Yellow', 'golden': 'Yellow',

    # Special
    'multicolor': 'Multicolor',
}

# The consolidated list of broad color groups Gemini is forced to pick from
COLOR_GROUPS = [
    "Beige", "Black", "Blue", "Brown", "Green", "Grey", "Multicolor", 
    "Orange", "Pink", "Purple", "Red", "White", "Yellow"
]

# Mapping for UI color squares (Hex/CSS values) for the 12 broad groups
COLOR_HEX_MAPPING = {
    'Beige': '#F5F5DC',
    'Black': '#000000',
    'Blue': '#0000FF',
    'Brown': '#8B4513',
    'Green': '#008000',
    'Grey': '#808080',
    'Multicolor': 'linear-gradient(to right, red, orange, yellow, green, blue, indigo, violet)',
    'Orange': '#FFA500',
    'Pink': '#FFC0CB',
    'Purple': '#800080',
    'Red': '#FF0000',
    'White': '#FFFFFF',
    'Yellow': '#FFFF00',
}

def get_color_family(specific_color):
    if not specific_color: return "Unknown"
    clean_color = specific_color.lower().strip()
    return COLOR_MAPPING.get(clean_color, clean_color.capitalize())
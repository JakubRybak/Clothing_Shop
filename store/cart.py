from .models import ProductVariant

class Cart:
    def __init__(self, request):
        """
        Initialize the cart.
        """
        self.session = request.session
        cart = self.session.get('cart')

        if not cart:
            # Save an empty cart in the session
            cart = self.session['cart'] = {}
        
        self.cart = cart

    def add(self, variant_id):
        """
        Add a product variant to the cart or update its quantity.
        """
        variant_id = str(variant_id)
        
        if variant_id in self.cart:
            self.cart[variant_id] += 1
        else:
            self.cart[variant_id] = 1
            
        self.save()

    def __iter__(self):
        """
        Iterate over the items in the cart and get the products from the database.
        """
        product_ids = self.cart.keys()
        # Get the product objects and add them to the cart
        variants = ProductVariant.objects.filter(id__in=product_ids)
        
        cart = self.cart.copy()
        for variant in variants:
            cart[str(variant.id)] = {'variant': variant, 'quantity': cart[str(variant.id)]}

        for item in cart.values():
            if isinstance(item, dict) and 'variant' in item: # Ensure valid item structure
                item['price'] = item['variant'].product.price
                item['total_price'] = item['price'] * item['quantity']
                yield item

    def __len__(self):
        """
        Count all items in the cart.
        """
        return sum(self.cart.values())
        
    def get_total_price(self):
        """
        Calculate the total cost of the cart.
        """
        # We need to re-fetch variants here or rely on __iter__ but __iter__ is a generator
        # A simpler way is to fetch variants again or implement logic similar to __iter__
        total = 0
        product_ids = self.cart.keys()
        variants = ProductVariant.objects.filter(id__in=product_ids)
        for variant in variants:
            qty = self.cart[str(variant.id)]
            total += variant.product.price * qty
        return total

    def save(self):
        self.session.modified = True
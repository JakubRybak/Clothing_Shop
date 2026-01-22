from django.test import TestCase, Client
from django.urls import reverse
from .models import Category, Product, ProductVariant, ProductImage
import json
from django.core.files.uploadedfile import SimpleUploadedFile

class VisualSearchTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category_coat = Category.objects.create(name="Coat", slug="coat")
        self.category_pants = Category.objects.create(name="Pants", slug="pants")

        self.coat = Product.objects.create(
            name="Winter Coat", slug="winter-coat", price=100.00
        )
        self.coat.categories.add(self.category_coat)
        
        self.pants = Product.objects.create(
            name="Jeans", slug="jeans", price=50.00
        )
        self.pants.categories.add(self.category_pants)
        
        # Variants and Images are needed because logic checks for display_variant or images
        self.coat_variant = ProductVariant.objects.create(
            product=self.coat, size="L", color="Black", stock_quantity=10
        )
        self.coat_image = ProductImage.objects.create(
            variant=self.coat_variant,
            image=SimpleUploadedFile(name='coat.jpg', content=b'', content_type='image/jpeg')
        )

        self.pants_variant = ProductVariant.objects.create(
            product=self.pants, size="M", color="Blue", stock_quantity=10
        )
        self.pants_image = ProductImage.objects.create(
            variant=self.pants_variant,
            image=SimpleUploadedFile(name='pants.jpg', content=b'', content_type='image/jpeg')
        )

    def test_filter_examples_grouped_response(self):
        items_data = [
            {'category': 'Coat', 'color': 'Black', 'features': {}},
            {'category': 'Pants', 'color': 'Blue', 'features': {}}
        ]
        
        response = self.client.post(reverse('visual_search'), {
            'action': 'filter_examples',
            'items_data': json.dumps(items_data)
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('example_products', data)
        example_products = data['example_products']
        
        # Check structure
        self.assertIsInstance(example_products, list)
        self.assertEqual(len(example_products), 2)
        
        # Check first group (Coat) - order isn't guaranteed if list processing doesn't enforce it,
        # but the input list is ordered and loop preserves it.
        
        # Find Coat group
        coat_group = next((g for g in example_products if g['category'] == 'Coat'), None)
        self.assertIsNotNone(coat_group)
        self.assertEqual(len(coat_group['products']), 1)
        self.assertEqual(coat_group['products'][0]['product_name'], 'Winter Coat')
        
        # Find Pants group
        pants_group = next((g for g in example_products if g['category'] == 'Pants'), None)
        self.assertIsNotNone(pants_group)
        self.assertEqual(len(pants_group['products']), 1)
        self.assertEqual(pants_group['products'][0]['product_name'], 'Jeans')
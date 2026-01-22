import json
import requests
import random
import concurrent.futures
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils.text import slugify
from store.models import Category, Product, ProductVariant, ProductImage
from store.ai_utils import generate_product_features

class Command(BaseCommand):
    help = 'Import products from a JSON file, drop old ones, and optionally generate AI features'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, default='results_subset.json', help='The JSON file to import')
        parser.add_argument('--ai', action='store_true', help='Generate AI features using multithreading')
        parser.add_argument('--workers', type=int, default=5, help='Number of parallel AI workers')

    def handle(self, *args, **options):
        file_path = options['file']
        use_ai = options['ai']
        max_workers = options['workers']

        # 1. Clear existing data
        self.stdout.write(self.style.WARNING(f"Dropping existing products..."))
        Product.objects.all().delete()
        
        # 2. Setup Category
        category_name = "Coats"
        category, _ = Category.objects.get_or_create(
            name=category_name,
            defaults={'slug': slugify(category_name)}
        )

        # 3. Load JSON
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File {file_path} not found!"))
            return

        self.stdout.write(f"Found {len(data)} items in {file_path}. Starting import...")

        imported_product_ids = []
        image_cache = {}

        for item in data:
            name = item.get('name')
            sku = item.get('sku')
            description = item.get('description', '')
            price = item.get('price', '0.00').replace(',', '.')
            color = item.get('color', 'Universal')
            image_urls = item.get('images', [])

            if not sku or not name:
                continue

            try:
                product, created = Product.objects.get_or_create(
                    sku=sku,
                    defaults={
                        'name': name,
                        'description': description,
                        'price': float(price),
                    }
                )
                
                if created:
                    product.categories.add(category)
                
                if product.id not in imported_product_ids:
                    imported_product_ids.append(product.id)

                # Sizes & Stock
                selected_sizes = random.sample(['S', 'M', 'L'], random.randint(1, 3))

                # Image Handling (Cache by color to avoid re-downloading)
                cache_key = f"{sku}_{color}"
                if cache_key not in image_cache:
                    downloaded = []
                    for i, img_url in enumerate(image_urls[:5]):
                        try:
                            resp = requests.get(img_url, timeout=5)
                            if resp.status_code == 200:
                                ext = img_url.split('.')[-1].split('?')[0] or 'jpg'
                                filename = f"{sku}_{slugify(color)}_{i}.{ext}"
                                downloaded.append({'name': filename, 'content': resp.content, 'main': (i==0)})
                        except: continue
                    image_cache[cache_key] = downloaded

                for size in selected_sizes:
                    variant = ProductVariant.objects.create(
                        product=product, color=color, size=size, stock_quantity=random.randint(5, 50)
                    )
                    for img_data in image_cache[cache_key]:
                        pi = ProductImage(variant=variant, is_main=img_data['main'])
                        pi.image.save(img_data['name'], ContentFile(img_data['content']), save=True)

                self.stdout.write(f"Imported: {name} ({color})")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error {sku}: {e}"))

        # 4. Optional AI Feature Generation (Multithreaded)
        if use_ai and imported_product_ids:
            self.stdout.write(self.style.SUCCESS(f"\nStarting AI Generation for {len(imported_product_ids)} products using {max_workers} workers..."))
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Map the function to the product IDs
                future_to_id = {executor.submit(generate_product_features, pid): pid for pid in imported_product_ids}
                
                completed = 0
                for future in concurrent.futures.as_completed(future_to_id):
                    pid = future_to_id[future]
                    try:
                        future.result()
                        completed += 1
                        if completed % 5 == 0:
                            self.stdout.write(f"AI Progress: {completed}/{len(imported_product_ids)}")
                    except Exception as exc:
                        self.stdout.write(self.style.ERROR(f"Product {pid} generated an exception: {exc}"))

        self.stdout.write(self.style.SUCCESS("\n--- ALL TASKS FINISHED ---"))

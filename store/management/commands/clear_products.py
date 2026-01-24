from django.core.management.base import BaseCommand
from store.models import Product

class Command(BaseCommand):
    help = 'Deletes ALL products from the database.'

    def handle(self, *args, **options):
        count = Product.objects.count()
        self.stdout.write(self.style.WARNING(f"Deleting {count} products..."))
        Product.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("All products deleted successfully."))

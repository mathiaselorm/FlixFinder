from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Train the SVD recommender and save the model to disk and storage."

    def handle(self, *args, **options):
        # Import here to ensure Django settings are loaded
        from recommendations.utils import train_and_save_model

        self.stdout.write("Training recommendation model…")
        algo = train_and_save_model()
        self.stdout.write(self.style.SUCCESS("✅ Model trained and saved successfully!"))
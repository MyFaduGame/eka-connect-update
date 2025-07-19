from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Starts the MQTT processor"

    def handle(self, *args, **kwargs):
        from devices.processor import main
        main()
import logging
from django.core.management.base import BaseCommand
from core_functions import SystemManager


class Command(BaseCommand):
    help = ""

    def handle(self, *args, **options):

        manager = SystemManager()
        manager.run_system()

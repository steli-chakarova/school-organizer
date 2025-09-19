from django.core.management.base import BaseCommand
from organizer.models import Subject


class Command(BaseCommand):
    help = 'Seed the database with subjects'

    def handle(self, *args, **options):
        subjects = [
            'Математика',
            'Физическо',
            'БЕЛ – Писане',
            'БЕЛ – Четене',
            'Човекът и природата',
            'Английски език',
            'Изобразително',
            'Човекът и обществото',
            'Български език (ИУЧ)',
            'Час на класа',
            'Музика',
            'БЕЛ – Развитие на речта',
            'БЕЛ – Извънкласно четене',
            'Спорт',
            'Компютърно моделиране',
            'Технологии',
            'Математика (ИУЧ)'
        ]
        
        created_count = 0
        for subject_name in subjects:
            subject, created = Subject.objects.get_or_create(name=subject_name)
            if created:
                created_count += 1
                self.stdout.write(f'Created subject: {subject_name}')
            else:
                self.stdout.write(f'Subject already exists: {subject_name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully processed {len(subjects)} subjects. Created {created_count} new subjects.')
        )

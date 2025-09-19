from django.core.management.base import BaseCommand
from django.db import transaction
from organizer.models import Subject, WeeklySchedule


class Command(BaseCommand):
    help = 'Seed the database with weekly schedule'

    def handle(self, *args, **options):
        # Weekly program data
        weekly_program = {
            1: [  # Monday
                'Математика',
                'Физическо',
                'БЕЛ – Писане',
                'БЕЛ – Четене',
                'Човекът и природата',
                'Английски език'
            ],
            2: [  # Tuesday
                'БЕЛ – Четене',
                'Математика',
                'Изобразително',
                'Човекът и обществото',
                'Български език (ИУЧ)',
                'Час на класа'
            ],
            3: [  # Wednesday
                'Музика',
                'Английски език',
                'Математика (ИУЧ)',
                'БЕЛ – Развитие на речта',
                'БЕЛ – Извънкласно четене',
                'Спорт'
            ],
            4: [  # Thursday
                'Компютърно моделиране',
                'БЕЛ – Четене',
                'Музика',
                'Математика',
                'Човекът и обществото',
                'Английски език'
            ],
            5: [  # Friday
                'БЕЛ – Писане',
                'Физическо',
                'БЕЛ – ИУЧ',
                'Технологии',
                'Изобразително'
            ]
        }
        
        with transaction.atomic():
            # Clear existing schedule
            WeeklySchedule.objects.all().delete()
            self.stdout.write('Cleared existing weekly schedule')
            
            # Create new schedule
            created_count = 0
            for day_of_week, subject_names in weekly_program.items():
                for position, subject_name in enumerate(subject_names):
                    try:
                        subject = Subject.objects.get(name=subject_name)
                        WeeklySchedule.objects.create(
                            day_of_week=day_of_week,
                            subject=subject,
                            position=position
                        )
                        created_count += 1
                        self.stdout.write(f'Added {subject_name} to day {day_of_week} at position {position}')
                    except Subject.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'Subject not found: {subject_name}')
                        )
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {created_count} weekly schedule entries')
            )

from django.core.management.base import BaseCommand
from organizer.models import Subject, Book


class Command(BaseCommand):
    help = 'Seed the database with books'

    def handle(self, *args, **options):
        # Books for individual subjects
        subject_books = {
            'Математика': [
                'Учебник',
                'Учебна тетрадка 1',
                'Учебна тетрадка 2',
                'Сборник'
            ],
            'Човекът и природата': [
                'Учебник',
                'Учебна тетрадка'
            ],
            'Английски език': [
                'Учебник',
                'Учебна тетрадка'
            ],
            'Изобразително': [
                'Учебник'
            ],
            'Човекът и обществото': [
                'Учебник',
                'Учебна тетрадка',
                'Атлас'
            ],
            'Български език (ИУЧ)': [
                'Помагало'
            ],
            'Час на класа': [
                'Помагало'
            ],
            'Музика': [
                'Учебник',
                'Учебна тетрадка'
            ],
            'Компютърно моделиране': [
                'Учебник'
            ],
            'Технологии': [
                'Учебник'
            ],
            'Математика (ИУЧ)': [
                'Мат и Ема'
            ]
        }
        
        # Shared books for BЕЛ subjects
        bel_books = [
            'Учебник',
            'Учебна тетрадка 1',
            'Учебна тетрадка 2',
            'Чета с разбиране',
            'Читанка',
            'Тетрадка към читанка',
            'Езикови задачи'
        ]
        
        bel_subjects = [
            'БЕЛ – Развитие на речта',
            'БЕЛ – Писане',
            'БЕЛ – Четене',
            'БЕЛ – Извънкласно четене'
        ]
        
        created_count = 0
        
        # Add books for individual subjects
        for subject_name, book_titles in subject_books.items():
            try:
                subject = Subject.objects.get(name=subject_name)
                for book_title in book_titles:
                    book, created = Book.objects.get_or_create(
                        subject=subject,
                        title=book_title
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(f'Created book: {book_title} for {subject_name}')
                    else:
                        self.stdout.write(f'Book already exists: {book_title} for {subject_name}')
            except Subject.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Subject not found: {subject_name}')
                )
        
        # Add shared books for BЕЛ subjects
        for subject_name in bel_subjects:
            try:
                subject = Subject.objects.get(name=subject_name)
                for book_title in bel_books:
                    book, created = Book.objects.get_or_create(
                        subject=subject,
                        title=book_title
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(f'Created shared book: {book_title} for {subject_name}')
                    else:
                        self.stdout.write(f'Shared book already exists: {book_title} for {subject_name}')
            except Subject.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Subject not found: {subject_name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} new books')
        )

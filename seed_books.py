#!/usr/bin/env python3
"""
Seed script for populating the Book table with textbooks and workbooks.
This script assigns books to subjects and handles shared books between BЕЛ subjects.
Can be run multiple times safely without duplicating data.
"""

from app import app
from models import db
from models.database import Subject, Book

def get_or_create_subject(name):
    """Get existing subject or create if it doesn't exist."""
    subject = Subject.query.filter_by(name=name).first()
    if not subject:
        subject = Subject(name=name)
        db.session.add(subject)
        db.session.flush()  # Get the ID
        print(f"  + Created subject: {name}")
    return subject

def add_books_for_subject(subject_name, book_titles):
    """Add books for a specific subject."""
    subject = get_or_create_subject(subject_name)
    added_count = 0
    
    for book_title in book_titles:
        # Check if book already exists for this subject
        existing_book = Book.query.filter_by(
            subject_id=subject.id, 
            title=book_title
        ).first()
        
        if not existing_book:
            book = Book(subject_id=subject.id, title=book_title)
            db.session.add(book)
            added_count += 1
            print(f"    + Added: {book_title}")
        else:
            print(f"    - Already exists: {book_title}")
    
    return added_count

def add_shared_books_for_bel_subjects():
    """Add shared books for all BЕЛ subjects."""
    bel_subjects = [
        "БЕЛ – Развитие на речта",
        "БЕЛ – Писане", 
        "БЕЛ – Четене",
        "БЕЛ – Извънкласно четене"
    ]
    
    shared_books = [
        "Учебник",
        "Учебна тетрадка 1",
        "Учебна тетрадка 2", 
        "Чета с разбиране",
        "Читанка",
        "Тетрадка към читанка",
        "Езикови задачи"
    ]
    
    print("Adding shared books for BЕЛ subjects...")
    total_added = 0
    
    for subject_name in bel_subjects:
        print(f"  {subject_name}:")
        added = add_books_for_subject(subject_name, shared_books)
        total_added += added
    
    return total_added

def seed_books():
    """Main function to seed all books."""
    print("=" * 60)
    print("SCHOOL ORGANIZER - BOOKS SEEDING")
    print("=" * 60)
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        print("Database tables created/verified\n")
        
        total_books_added = 0
        
        # Individual subject books
        subject_books = {
            "Математика": [
                "Учебник",
                "Учебна тетрадка 1", 
                "Учебна тетрадка 2",
                "Сборник"
            ],
            "Човекът и природата": [
                "Учебник",
                "Учебна тетрадка"
            ],
            "Английски език": [
                "Учебник",
                "Учебна тетрадка"
            ],
            "Изобразително": [
                "Учебник"
            ],
            "Човекът и обществото": [
                "Учебник",
                "Учебна тетрадка",
                "Атлас"
            ],
            "Български език (ИУЧ)": [
                "Помагало"
            ],
            "Час на класа": [
                "Помагало"
            ],
            "Музика": [
                "Учебник",
                "Учебна тетрадка"
            ],
            "Компютърно моделиране": [
                "Учебник"
            ],
            "Технологии": [
                "Учебник"
            ]
        }
        
        print("Adding individual subject books...")
        for subject_name, books in subject_books.items():
            print(f"  {subject_name}:")
            added = add_books_for_subject(subject_name, books)
            total_books_added += added
        
        # Add special book for "Математика (ИУЧ)" - this is a different subject
        print(f"  Математика (ИУЧ):")
        added = add_books_for_subject("Математика (ИУЧ)", ["Мат и Ема"])
        total_books_added += added
        
        print()
        
        # Add shared books for BЕЛ subjects
        bel_books_added = add_shared_books_for_bel_subjects()
        total_books_added += bel_books_added
        
        db.session.commit()
        
        print("\n" + "=" * 60)
        print("BOOKS SEEDING COMPLETE!")
        print(f"Total books added: {total_books_added}")
        print("=" * 60)
        
        # Show summary by subject
        print("\nSUMMARY BY SUBJECT:")
        print("-" * 40)
        all_subjects = Subject.query.all()
        for subject in all_subjects:
            book_count = Book.query.filter_by(subject_id=subject.id).count()
            print(f"{subject.name}: {book_count} books")

def main():
    """Main entry point."""
    seed_books()

if __name__ == "__main__":
    main()

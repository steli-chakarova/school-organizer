#!/usr/bin/env python3
"""
Seed script for school_organizer database.
This script populates the database with subjects and weekly schedule.
Can be run multiple times safely without duplicating data.
"""

from app import app
from models import db
from models.database import Subject, WeeklySchedule

def seed_subjects():
    """Add subjects to the database if they don't exist."""
    subjects_data = [
        "Математика",
        "Физическо",
        "БЕЛ – Писане",
        "БЕЛ – Четене",
        "Човекът и природата",
        "Английски език",
        "Изобразително",
        "Човекът и обществото",
        "Български език (ИУЧ)",
        "Час на класа",
        "Музика",
        "БЕЛ – Развитие на речта",
        "БЕЛ – Извънкласно четене",
        "Спорт",
        "Компютърно моделиране",
        "Технологии"
    ]
    
    print("Adding subjects...")
    added_count = 0
    
    for subject_name in subjects_data:
        # Check if subject already exists
        existing_subject = Subject.query.filter_by(name=subject_name).first()
        if not existing_subject:
            subject = Subject(name=subject_name)
            db.session.add(subject)
            added_count += 1
            print(f"  + Added: {subject_name}")
        else:
            print(f"  - Already exists: {subject_name}")
    
    db.session.commit()
    print(f"Subjects: {added_count} new subjects added\n")
    return added_count

def seed_weekly_schedule():
    """Add weekly schedule to the database."""
    # Clear existing schedule first
    WeeklySchedule.query.delete()
    print("Cleared existing weekly schedule")
    
    # Define the weekly program
    weekly_program = {
        1: [  # Monday
            "Математика",
            "Физическо", 
            "БЕЛ – Писане",
            "БЕЛ – Четене",
            "Човекът и природата",
            "Английски език"
        ],
        2: [  # Tuesday
            "БЕЛ – Четене",
            "Математика",
            "Изобразително",
            "Човекът и обществото",
            "Български език (ИУЧ)",
            "Час на класа"
        ],
        3: [  # Wednesday
            "Музика",
            "Английски език",
            "Математика",
            "БЕЛ – Развитие на речта",
            "БЕЛ – Извънкласно четене",
            "Спорт"
        ],
        4: [  # Thursday
            "Компютърно моделиране",
            "БЕЛ – Четене",
            "Музика",
            "Математика",
            "Човекът и обществото",
            "Английски език"
        ],
        5: [  # Friday
            "БЕЛ – Писане",
            "Физическо",
            "БЕЛ – Писане",  # Note: This appears to be a duplicate in the original data
            "Технологии",
            "Изобразително"
        ]
    }
    
    print("Adding weekly schedule...")
    total_entries = 0
    
    for day_of_week, subjects in weekly_program.items():
        day_names = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday"}
        print(f"  {day_names[day_of_week]} (day {day_of_week}):")
        
        for position, subject_name in enumerate(subjects):
            # Find the subject by name
            subject = Subject.query.filter_by(name=subject_name).first()
            if subject:
                schedule_entry = WeeklySchedule(
                    day_of_week=day_of_week,
                    subject_id=subject.id,
                    position=position
                )
                db.session.add(schedule_entry)
                total_entries += 1
                print(f"    {position + 1}. {subject_name}")
            else:
                print(f"    ERROR: Subject '{subject_name}' not found!")
    
    db.session.commit()
    print(f"Weekly schedule: {total_entries} entries added\n")
    return total_entries

def main():
    """Main function to run the seeding process."""
    print("=" * 50)
    print("SCHOOL ORGANIZER - DATABASE SEEDING")
    print("=" * 50)
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        print("Database tables created/verified\n")
        
        # Seed subjects
        subjects_added = seed_subjects()
        
        # Seed weekly schedule
        schedule_added = seed_weekly_schedule()
        
        print("=" * 50)
        print("SEEDING COMPLETE!")
        print(f"Subjects added: {subjects_added}")
        print(f"Schedule entries added: {schedule_added}")
        print("=" * 50)

if __name__ == "__main__":
    main()

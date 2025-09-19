from flask import Flask, render_template, request, redirect, url_for, flash
from models import db
from models.database import Subject, Book, WeeklySchedule, DailyEntry, DailyExtra, HomeworkEntry
from datetime import datetime, date, timedelta
import calendar
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school_organizer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db.init_app(app)

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    # Get all subjects for the dropdown
    subjects = Subject.query.all()
    
    # Get the weekly schedule
    weekly_schedule = WeeklySchedule.query.order_by(WeeklySchedule.day_of_week, WeeklySchedule.position).all()
    
    # Organize schedule by day
    schedule_by_day = {}
    for entry in weekly_schedule:
        day = entry.day_of_week
        if day not in schedule_by_day:
            schedule_by_day[day] = []
        schedule_by_day[day].append(entry)
    
    return render_template('home.html', subjects=subjects, schedule_by_day=schedule_by_day)

@app.route('/add_subject', methods=['POST'])
def add_subject():
    name = request.form.get('subject_name')
    if name:
        subject = Subject(name=name)
        db.session.add(subject)
        db.session.commit()
        flash('Subject added successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/add_book', methods=['POST'])
def add_book():
    subject_id = request.form.get('subject_id')
    title = request.form.get('book_title')
    if subject_id and title:
        book = Book(subject_id=subject_id, title=title)
        db.session.add(book)
        db.session.commit()
        flash('Book added successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/update_schedule', methods=['POST'])
def update_schedule():
    # Clear existing schedule
    WeeklySchedule.query.delete()
    
    # Add new schedule entries
    for day in range(1, 6):  # Monday to Friday
        subjects = request.form.getlist(f'subjects_{day}')
        for i, subject_id in enumerate(subjects):
            if subject_id:  # Only add if subject is selected
                schedule = WeeklySchedule(
                    day_of_week=day,
                    subject_id=subject_id,
                    position=i
                )
                db.session.add(schedule)
    
    db.session.commit()
    flash('Weekly schedule updated successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/today', methods=['GET', 'POST'])
def today():
    today_date = date.today()
    today_weekday = today_date.weekday() + 1  # Convert to 1=Monday, 7=Sunday
    
    if request.method == 'POST':
        # Handle form submission
        return handle_today_submission(today_date)
    
    # GET request - show today's form
    # Get today's subjects from weekly schedule
    today_subjects = WeeklySchedule.query.filter_by(day_of_week=today_weekday).order_by(WeeklySchedule.position).all()
    
    # Get existing entries for today
    existing_entries = DailyEntry.query.filter_by(date=today_date).all()
    existing_extras = []
    existing_homework = []
    for entry in existing_entries:
        extras = DailyExtra.query.filter_by(daily_entry_id=entry.id).all()
        existing_extras.extend(extras)
        homework = HomeworkEntry.query.filter_by(daily_entry_id=entry.id).all()
        existing_homework.extend(homework)
    
    # Get all books for dropdowns
    all_books = Book.query.all()
    books_by_subject = {}
    for book in all_books:
        if book.subject_id not in books_by_subject:
            books_by_subject[book.subject_id] = []
        books_by_subject[book.subject_id].append(book)
    
    return render_template('today.html', 
                         today_subjects=today_subjects,
                         existing_entries=existing_entries,
                         existing_extras=existing_extras,
                         existing_homework=existing_homework,
                         books_by_subject=books_by_subject,
                         today_date=today_date)

def handle_today_submission(today_date):
    """Handle the submission of today's form"""
    # Get all subjects for today
    today_weekday = today_date.weekday() + 1
    today_subjects = WeeklySchedule.query.filter_by(day_of_week=today_weekday).order_by(WeeklySchedule.position).all()
    
    # Clear existing entries for today
    existing_entries = DailyEntry.query.filter_by(date=today_date).all()
    for entry in existing_entries:
        # Delete associated extras and homework first
        DailyExtra.query.filter_by(daily_entry_id=entry.id).delete()
        HomeworkEntry.query.filter_by(daily_entry_id=entry.id).delete()
        db.session.delete(entry)
    
    # Process each subject
    for subject_schedule in today_subjects:
        subject_id = subject_schedule.subject_id
        
        # Get main entry data
        book_id = request.form.get(f'book_{subject_id}')
        pages = request.form.get(f'pages_{subject_id}')
        notes = request.form.get(f'notes_{subject_id}')
        
        # Create main entry if any data is provided
        if book_id or pages or notes:
            main_entry = DailyEntry(
                date=today_date,
                subject_id=subject_id,
                book_id=book_id if book_id else None,
                pages=pages if pages else None,
                notes=notes if notes else None
            )
            db.session.add(main_entry)
            db.session.flush()  # Get the ID
            
            # Process extra entries for this subject
            extra_count = 0
            while True:
                extra_book_id = request.form.get(f'extra_book_{subject_id}_{extra_count}')
                extra_pages = request.form.get(f'extra_pages_{subject_id}_{extra_count}')
                extra_notes = request.form.get(f'extra_notes_{subject_id}_{extra_count}')
                
                if not (extra_book_id or extra_pages or extra_notes):
                    break
                
                extra_entry = DailyExtra(
                    daily_entry_id=main_entry.id,
                    book_id=extra_book_id if extra_book_id else None,
                    pages=extra_pages if extra_pages else None,
                    notes=extra_notes if extra_notes else None
                )
                db.session.add(extra_entry)
                extra_count += 1
            
            # Process homework entries for this subject
            homework_count = 0
            while True:
                homework_book_id = request.form.get(f'homework_book_{subject_id}_{homework_count}')
                homework_pages = request.form.get(f'homework_pages_{subject_id}_{homework_count}')
                
                if not (homework_book_id or homework_pages):
                    break
                
                homework_entry = HomeworkEntry(
                    daily_entry_id=main_entry.id,
                    book_id=homework_book_id if homework_book_id else None,
                    pages=homework_pages if homework_pages else None
                )
                db.session.add(homework_entry)
                homework_count += 1
    
    db.session.commit()
    flash('Today\'s entries saved successfully!', 'success')
    return redirect(url_for('today'))

@app.route('/history')
def history():
    # Get current month and year from URL parameters
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    # If no year/month specified, use current date
    if not year or not month:
        today = date.today()
        year = today.year
        month = today.month
    
    # Get the selected date for viewing daily data
    selected_date = request.args.get('date')
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date = None
    
    # Generate calendar data
    cal_data = generate_calendar_data(year, month)
    
    # Get days with entries for highlighting
    days_with_entries = get_days_with_entries(year, month)
    
    # Get daily data if a date is selected
    daily_data = None
    if selected_date:
        daily_data = get_daily_data(selected_date)
    
    # Calculate previous and next month
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    return render_template('history.html',
                         year=year,
                         month=month,
                         cal_data=cal_data,
                         days_with_entries=days_with_entries,
                         selected_date=selected_date,
                         daily_data=daily_data,
                         prev_month=prev_month,
                         prev_year=prev_year,
                         next_month=next_month,
                         next_year=next_year,
                         calendar=calendar)

def generate_calendar_data(year, month):
    """Generate calendar data for the given month."""
    # Get the first day of the month and number of days
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    
    # Get the first day of the week (Monday = 0)
    first_weekday = first_day.weekday()
    
    # Calculate the start date of the calendar (might be from previous month)
    start_date = first_day - timedelta(days=first_weekday)
    
    # Generate 6 weeks of dates (42 days total)
    cal_dates = []
    for week in range(6):
        week_dates = []
        for day in range(7):
            current_date = start_date + timedelta(days=week * 7 + day)
            week_dates.append(current_date)
        cal_dates.append(week_dates)
    
    return cal_dates

def get_days_with_entries(year, month):
    """Get list of days that have entries for the given month."""
    # Get the first and last day of the month
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    
    # Query for entries in this month
    entries = DailyEntry.query.filter(
        DailyEntry.date >= first_day,
        DailyEntry.date <= last_day
    ).all()
    
    # Return list of day numbers that have entries
    return [entry.date.day for entry in entries]

def get_daily_data(selected_date):
    """Get all daily data for the selected date."""
    # Get main entries for the date
    entries = DailyEntry.query.filter_by(date=selected_date).all()
    
    daily_data = []
    for entry in entries:
        # Get subject name
        subject = Subject.query.get(entry.subject_id)
        subject_name = subject.name if subject else "Unknown Subject"
        
        # Get book name if book_id exists
        book_name = None
        if entry.book_id:
            book = Book.query.get(entry.book_id)
            book_name = book.title if book else "Unknown Book"
        
        # Get extra entries for this main entry
        extras = DailyExtra.query.filter_by(daily_entry_id=entry.id).all()
        extra_books = []
        for extra in extras:
            extra_book = Book.query.get(extra.book_id)
            extra_books.append({
                'book_name': extra_book.title if extra_book else "Unknown Book",
                'pages': extra.pages,
                'notes': extra.notes
            })
        
        # Get homework entries for this main entry
        homework_entries = HomeworkEntry.query.filter_by(daily_entry_id=entry.id).all()
        homework_books = []
        for homework in homework_entries:
            homework_book = Book.query.get(homework.book_id)
            homework_books.append({
                'book_name': homework_book.title if homework_book else "Unknown Book",
                'pages': homework.pages
            })
        
        daily_data.append({
            'subject_name': subject_name,
            'book_name': book_name,
            'pages': entry.pages,
            'notes': entry.notes,
            'extras': extra_books,
            'homework': homework_books
        })
    
    return daily_data

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

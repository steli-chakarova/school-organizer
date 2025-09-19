from . import db

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    
    # Relationship to Subject
    subject = db.relationship('Subject', backref='books')

class WeeklySchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)  # 1=Monday, 7=Sunday
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False)  # order of subject during the day
    
    # Relationship to Subject
    subject = db.relationship('Subject', backref='weekly_schedules')

class DailyEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=True)
    pages = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    subject = db.relationship('Subject', backref='daily_entries')
    book = db.relationship('Book', backref='daily_entries')
    extras = db.relationship('DailyExtra', backref='daily_entry', cascade='all, delete-orphan')
    homework_entries = db.relationship('HomeworkEntry', backref='daily_entry', cascade='all, delete-orphan')

class DailyExtra(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    daily_entry_id = db.Column(db.Integer, db.ForeignKey('daily_entry.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    pages = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    book = db.relationship('Book', backref='daily_extras')

class HomeworkEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    daily_entry_id = db.Column(db.Integer, db.ForeignKey('daily_entry.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    pages = db.Column(db.String(100), nullable=True)
    
    # Relationships
    book = db.relationship('Book', backref='homework_entries')

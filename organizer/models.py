from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('viewer', 'Viewer'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='teacher')
    email = models.EmailField(unique=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_teacher(self):
        return self.role == 'teacher'
    
    def is_viewer(self):
        return self.role == 'viewer'
    
    def can_edit(self, obj):
        """Check if user can edit the given object"""
        if self.is_admin():
            return True
        if self.is_teacher() and hasattr(obj, 'created_by'):
            return obj.created_by == self
        return False


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class Book(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='books')
    title = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} ({self.subject.name})"
    
    class Meta:
        ordering = ['title']


class WeeklySchedule(models.Model):
    DAY_CHOICES = [
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
    ]
    
    day_of_week = models.IntegerField(
        choices=DAY_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='weekly_schedules', null=True, blank=True)
    position = models.IntegerField(validators=[MinValueValidator(0)])
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    
    def __str__(self):
        return f"{self.get_day_of_week_display()} - {self.subject.name} (Position {self.position})"
    
    class Meta:
        ordering = ['day_of_week', 'position']


class DailyEntry(models.Model):
    date = models.DateField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='daily_entries')
    book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True, related_name='daily_entries')
    pages = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    important_notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.date} - {self.subject.name}"
    
    class Meta:
        ordering = ['date', 'subject__name']
        unique_together = ['date', 'subject']


class DailyExtra(models.Model):
    daily_entry = models.ForeignKey(DailyEntry, on_delete=models.CASCADE, related_name='extras')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='daily_extras')
    pages = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.daily_entry} - Extra: {self.book.title}"
    
    class Meta:
        ordering = ['id']


class HomeworkEntry(models.Model):
    daily_entry = models.ForeignKey(DailyEntry, on_delete=models.CASCADE, related_name='homework_entries')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='homework_entries')
    pages = models.CharField(max_length=100, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.daily_entry} - Homework: {self.book.title}"
    
    class Meta:
        ordering = ['id']
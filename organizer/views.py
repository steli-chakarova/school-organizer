from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
import json
from django.contrib.auth.forms import UserCreationForm
from django import forms
from datetime import datetime, date as date_module, timedelta
import calendar

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak, Frame, PageTemplate, Image, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

from pdf2image import convert_from_bytes
from io import BytesIO
import tempfile
import os
import base64
from PIL import Image as PILImage

from .models import Subject, Book, WeeklySchedule, DailyEntry, DailyExtra, HomeworkEntry, User


def is_mobile_device(request):
    """Simple mobile device detection based on user agent"""
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone']
    return any(keyword in user_agent for keyword in mobile_keywords)


# Authentication Views
class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        template = 'mobile_login.html' if is_mobile_device(request) else 'login.html'
        return render(request, template)
    
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('home')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please fill in all fields.')
        
        template = 'mobile_login.html' if is_mobile_device(request) else 'login.html'
        return render(request, template)


class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.info(request, 'You have been logged out.')
        return redirect('login')


class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        template = 'mobile_register.html' if is_mobile_device(request) else 'register.html'
        return render(request, template)
    
    def post(self, request):
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        template = 'mobile_register.html' if is_mobile_device(request) else 'register.html'
        
        if not all([username, email, password1, password2]):
            messages.error(request, 'Please fill in all fields.')
            return render(request, template)
        
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, template)
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, template)
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return render(request, template)
        
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                role='teacher'  # Default role - all new users are teachers
            )
            login(request, user)
            messages.success(request, f'Account created successfully! Welcome, {user.username}!')
            return redirect('home')
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return render(request, template)


# Role-based access control mixins
class AdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_admin():
            messages.error(request, 'Access denied. Admin privileges required.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)


class TeacherOrAdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return redirect('login')
            if not (request.user.is_admin() or request.user.is_teacher()):
                messages.error(request, 'Access denied. Teacher or Admin privileges required.')
                return redirect('history')
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            # Handle any sync/async issues gracefully
            if 'SynchronousOnlyOperation' in str(e):
                # Fall back to basic authentication check
                if not hasattr(request, 'user') or not request.user.is_authenticated:
                    return redirect('login')
                return super().dispatch(request, *args, **kwargs)
            raise e


class ViewerOrAboveRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


class HomeView(View):
    def get(self, request):
        # Redirect anonymous users to login page
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Clear any target_user_id from session for regular users
        if 'target_user_id' in request.session:
            del request.session['target_user_id']
        
        # Show only personal projects for all users (including admin)
        subjects = Subject.objects.filter(created_by=request.user)
        # Only show schedules that reference subjects created by the current user
        weekly_schedule = WeeklySchedule.objects.filter(
            created_by=request.user, 
            is_active=True,
            subject__created_by=request.user
        ).select_related('subject').order_by('day_of_week', 'position')
        schedule_by_day = {}
        for entry in weekly_schedule:
            day = entry.day_of_week
            if day not in schedule_by_day:
                schedule_by_day[day] = []
            schedule_by_day[day].append(entry)
        
        # Check if there are any active schedules with subjects
        has_active_schedule = weekly_schedule.filter(subject__isnull=False).exists()
        show_schedule_management = has_active_schedule
        hide_schedule_management = not has_active_schedule
        
        template = 'mobile_home.html' if is_mobile_device(request) else 'home.html'
        return render(request, template, {
            'subjects': subjects,
            'all_subjects': subjects,  # For regular users, use their own subjects
            'schedule_by_day': schedule_by_day,
            'has_active_schedule': has_active_schedule,
            'show_schedule_management': show_schedule_management,
            'hide_schedule_management': hide_schedule_management
        })
    
    def post(self, request):
        if 'subject_name' in request.POST:
            # Add new subject
            subject_name = request.POST.get('subject_name')
            if subject_name:
                Subject.objects.get_or_create(name=subject_name, defaults={'created_by': request.user})
                messages.success(request, 'Subject added successfully!')
        
        elif 'subject_id' in request.POST and 'book_title' in request.POST:
            # Add new book
            subject_id = request.POST.get('subject_id')
            book_title = request.POST.get('book_title')
            if subject_id and book_title:
                try:
                    subject = Subject.objects.get(id=subject_id)
                    # Check if user can edit this subject
                    if not request.user.can_edit(subject):
                        messages.error(request, 'You can only add books to subjects you created!')
                        return redirect('home')
                    Book.objects.get_or_create(subject=subject, title=book_title, defaults={'created_by': request.user})
                    messages.success(request, 'Book added successfully!')
                except Subject.DoesNotExist:
                    messages.error(request, 'Subject not found!')
        
        elif 'update_schedule' in request.POST:
            # Update weekly schedule
            with transaction.atomic():
                # Disable old schedules instead of deleting them
                if request.user.is_admin():
                    WeeklySchedule.objects.filter(is_active=True).update(is_active=False)
                else:
                    WeeklySchedule.objects.filter(created_by=request.user, is_active=True).update(is_active=False)
                
                for day in range(1, 8):  # Monday to Sunday
                    subjects = request.POST.getlist(f'subjects_{day}')
                    # Filter out empty values
                    subjects = [s for s in subjects if s.strip()]
                    for i, subject_id in enumerate(subjects):
                        if subject_id:
                            try:
                                subject = Subject.objects.get(id=subject_id)
                                # Check if user can edit this subject
                                if request.user.can_edit(subject):
                                    WeeklySchedule.objects.create(
                                        day_of_week=day,
                                        subject=subject,
                                        position=i,
                                        created_by=request.user,
                                        is_active=True
                                )
                            except Subject.DoesNotExist:
                                pass
                
                messages.success(request, 'Weekly schedule updated successfully!')
        
        elif 'action' in request.POST and request.POST.get('action') == 'update_alias':
            # Update user alias
            alias = request.POST.get('alias', '').strip()
            request.user.alias = alias if alias else None
            request.user.save()
            messages.success(request, 'Display name updated successfully!')
        
        return redirect('home')


class HomeUserView(LoginRequiredMixin, View):
    def get(self, request, username, user_id):
        # Only admin users can access this page
        if not request.user.is_admin():
            return redirect('no_access')
        
        try:
            target_user = User.objects.get(username__iexact=username, id=user_id)
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('users')
        
        # Show only subjects created by the target user (for adding books)
        subjects = Subject.objects.filter(created_by=target_user).order_by('name')
        # Show all subjects for schedule assignment (admin can assign any subject)
        all_subjects = Subject.objects.all().order_by('name')
        # Show all active schedules for the target user (admin can see all)
        weekly_schedule = WeeklySchedule.objects.filter(
            created_by=target_user, 
            is_active=True
        ).select_related('subject').order_by('day_of_week', 'position')
        schedule_by_day = {}
        for entry in weekly_schedule:
            day = entry.day_of_week
            if day not in schedule_by_day:
                schedule_by_day[day] = []
            schedule_by_day[day].append(entry)
        
        # Check if there are any active schedules with subjects
        has_active_schedule = weekly_schedule.filter(subject__isnull=False).exists()
        show_schedule_management = has_active_schedule
        hide_schedule_management = not has_active_schedule
        
        # Set target user in session for API calls
        request.session['target_user_id'] = target_user.id
        
        template = 'mobile_home.html' if is_mobile_device(request) else 'home.html'
        return render(request, template, {
            'subjects': subjects,
            'all_subjects': all_subjects,
            'schedule_by_day': schedule_by_day,
            'has_active_schedule': has_active_schedule,
            'show_schedule_management': show_schedule_management,
            'hide_schedule_management': hide_schedule_management,
            'target_user': target_user,
            'is_admin_view': True
        })
    
    def post(self, request, username, user_id):
        # Only admin users can access this page
        if not request.user.is_admin():
            return redirect('no_access')
        
        try:
            target_user = User.objects.get(username__iexact=username, id=user_id)
            # Set target user in session for API calls
            request.session['target_user_id'] = target_user.id
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('users')
        
        if 'subject_name' in request.POST:
            # Add new subject for target user
            subject_name = request.POST.get('subject_name')
            if subject_name:
                Subject.objects.get_or_create(name=subject_name, defaults={'created_by': target_user})
                messages.success(request, f'Subject added successfully for {target_user.username}!')
        
        elif 'subject_id' in request.POST and 'book_title' in request.POST:
            # Add new book for target user
            subject_id = request.POST.get('subject_id')
            book_title = request.POST.get('book_title')
            if subject_id and book_title:
                try:
                    subject = Subject.objects.get(id=subject_id)
                    # Admin can add books to any subject
                    Book.objects.create(
                        title=book_title,
                        subject=subject,
                        created_by=target_user
                    )
                    messages.success(request, f'Book added successfully for {target_user.username}!')
                except Subject.DoesNotExist:
                    messages.error(request, 'Subject not found!')
        
        elif 'update_schedule' in request.POST:
            # Update weekly schedule for target user
            with transaction.atomic():
                # Disable old schedules for target user
                WeeklySchedule.objects.filter(created_by=target_user, is_active=True).update(is_active=False)
                
                for day in range(1, 8):  # Monday to Sunday
                    subjects = request.POST.getlist(f'subjects_{day}')
                    # Filter out empty values
                    subjects = [s for s in subjects if s.strip()]
                    for i, subject_id in enumerate(subjects):
                        if subject_id:
                            try:
                                subject = Subject.objects.get(id=subject_id)
                                # Admin can use any subject for any user's schedule
                                WeeklySchedule.objects.create(
                                    day_of_week=day,
                                    subject=subject,
                                    position=i,
                                    created_by=target_user,
                                    is_active=True
                                )
                            except Subject.DoesNotExist:
                                pass
                
                messages.success(request, f'Weekly schedule updated successfully for {target_user.username}!')
        
        elif 'action' in request.POST:
            # Handle schedule management actions
            action = request.POST.get('action')
            
            if action == 'create_new':
                # Create a new empty schedule for target user
                with transaction.atomic():
                    # Disable current active schedules for target user
                    WeeklySchedule.objects.filter(created_by=target_user, is_active=True).update(is_active=False)
                    
                    # Create empty schedule for each day
                    for day in range(1, 8):  # Monday to Sunday
                        WeeklySchedule.objects.create(
                            day_of_week=day,
                            subject=None,  # Empty subject
                            position=0,
                            created_by=target_user,
                            is_active=True
                        )
                    
                    messages.success(request, f'New empty weekly schedule created for {target_user.username}!')
            
            elif action == 'disable_current':
                # Disable current active schedule for target user
                with transaction.atomic():
                    disabled_count = WeeklySchedule.objects.filter(created_by=target_user, is_active=True).update(is_active=False)
                    
                    if disabled_count > 0:
                        messages.success(request, f'Deleted {disabled_count} schedule entries for {target_user.username}!')
                    else:
                        messages.info(request, f'No active schedule to delete for {target_user.username}!')
        
        return redirect('home_user', username=username, user_id=user_id)


class ScheduleManagementView(TeacherOrAdminRequiredMixin, View):
    def post(self, request):
        action = request.POST.get('action')
        
        if action == 'create_new':
            # Create a new empty schedule (disable current, create new empty one)
            with transaction.atomic():
                # Disable current active schedules
                if request.user.is_admin():
                    WeeklySchedule.objects.filter(is_active=True).update(is_active=False)
                else:
                    WeeklySchedule.objects.filter(created_by=request.user, is_active=True).update(is_active=False)
                
                # Create empty schedule for each day
                for day in range(1, 8):  # Monday to Sunday
                    WeeklySchedule.objects.create(
                        day_of_week=day,
                        subject=None,  # Empty subject
                        position=0,
                        created_by=request.user,
                        is_active=True
                    )
                
                messages.success(request, 'New empty weekly schedule created!')
        
        elif action == 'disable_current':
            # Disable current active schedule
            with transaction.atomic():
                if request.user.is_admin():
                    disabled_count = WeeklySchedule.objects.filter(is_active=True).update(is_active=False)
                else:
                    disabled_count = WeeklySchedule.objects.filter(created_by=request.user, is_active=True).update(is_active=False)
                
                if disabled_count > 0:
                    messages.success(request, f'Deleted {disabled_count} schedule entries!')
                else:
                    messages.info(request, 'No active schedule to delete!')
        
        return redirect('home')


class TodayView(View):
    def get(self, request, date=None, username=None, user_id=None):
        # Simple authentication check without session access
        if not hasattr(request, 'user') or not request.user or request.user.is_anonymous:
            return redirect('history')
        
        # Check if user has required permissions
        if not (request.user.is_admin() or request.user.is_teacher()):
            messages.error(request, 'Access denied. Teacher or Admin privileges required.')
            return redirect('history')
        
        # Determine target user and edit permissions
        target_user = request.user  # Default to current user
        can_edit = True  # Default to True for own data
        
        if username and user_id:
            try:
                target_user = User.objects.get(username__iexact=username, id=user_id)
                # Check edit permissions: can edit own data or if admin
                can_edit = (target_user == request.user) or request.user.is_admin()
            except User.DoesNotExist:
                # If user doesn't exist, redirect to own today page
                return redirect('today')
        if date:
            try:
                # Parse date from URL parameter (format: DD-MM-YY)
                today_date = datetime.strptime(date, '%d-%m-%y').date()
            except ValueError:
                # If date format is invalid, fall back to today
                from datetime import date as date_module
                today_date = date_module.today()
        else:
            from datetime import date as date_module
            today_date = date_module.today()
        
        today_weekday = today_date.weekday() + 1  # Convert to 1=Monday, 7=Sunday
        
        # Get today's subjects - simple approach: show daily entries + unused weekly schedule subjects
        if request.user.is_admin():
            # Admin can see all data, but filter by target user if specified
            weekly_subjects = WeeklySchedule.objects.filter(day_of_week=today_weekday, is_active=True, subject__isnull=False, created_by=target_user).select_related('subject').order_by('position')
        else:  # Teacher - only their own data
            weekly_subjects = WeeklySchedule.objects.filter(day_of_week=today_weekday, created_by=target_user, is_active=True, subject__isnull=False).select_related('subject').order_by('position')
        
        # Get existing daily entries
        existing_entries = DailyEntry.objects.filter(date=today_date, created_by=target_user).select_related('subject', 'book')
        
        # Build today_subjects: show weekly schedule in order, replace with daily entries when they exist
        today_subjects = []
        
        # Create a map of daily entries by subject ID for quick lookup
        daily_entries_by_subject = {}
        for entry in existing_entries:
            if entry.subject.id not in daily_entries_by_subject:
                daily_entries_by_subject[entry.subject.id] = []
            daily_entries_by_subject[entry.subject.id].append(entry)
        
        # Go through weekly schedule in order
        for weekly_schedule in weekly_subjects:
            # Check if this subject has daily entries
            if weekly_schedule.subject.id in daily_entries_by_subject:
                # Replace with daily entry (keep the same position)
                entry = daily_entries_by_subject[weekly_schedule.subject.id][0]  # Take first entry
                mock_schedule = type('MockSchedule', (), {
                    'subject': entry.subject,
                    'position': weekly_schedule.position,
                    'day_of_week': today_weekday,
                    'is_active': True,
                    'created_by': target_user
                })()
                today_subjects.append(mock_schedule)
            else:
                # No daily entry for this subject, use weekly schedule
                today_subjects.append(weekly_schedule)
        
        # Add any daily entries that are NOT in the weekly schedule (new subjects)
        weekly_subject_ids = {schedule.subject.id for schedule in weekly_subjects}
        for entry in existing_entries:
            if entry.subject.id not in weekly_subject_ids:
                # This is a new subject not in weekly schedule - add it at the end
                mock_schedule = type('MockSchedule', (), {
                    'subject': entry.subject,
                    'position': 999,  # High position for new subjects
                    'day_of_week': today_weekday,
                    'is_active': True,
                    'created_by': target_user
                })()
                today_subjects.append(mock_schedule)
        existing_extras = []
        existing_homework = []
        
        for entry in existing_entries:
            extras = DailyExtra.objects.filter(daily_entry=entry).select_related('book')
            existing_extras.extend(extras)
            homework = HomeworkEntry.objects.filter(daily_entry=entry).select_related('book')
            existing_homework.extend(homework)
        
        # Get all books for dropdowns
        all_books = Book.objects.select_related('subject').all()
        books_by_subject = {}
        for book in all_books:
            if book.subject.id not in books_by_subject:
                books_by_subject[book.subject.id] = []
            books_by_subject[book.subject.id].append(book)
        
        # Get all subjects for the dropdown (filtered by target user)
        if request.user.is_admin():
            # Admin can see all subjects, but filter by target user if specified
            all_subjects = Subject.objects.filter(created_by=target_user).order_by('name')
        else:  # Teacher - only their own subjects
            all_subjects = Subject.objects.filter(created_by=target_user).order_by('name')
        
        template = 'mobile_today.html' if is_mobile_device(request) else 'today.html'
        return render(request, template, {
            'today_subjects': today_subjects,
            'existing_entries': existing_entries,
            'existing_extras': existing_extras,
            'existing_homework': existing_homework,
            'books_by_subject': books_by_subject,
            'today_date': today_date,
            'subjects': all_subjects,
            'target_user': target_user,
            'can_edit': can_edit
        })
    
    def post(self, request, date=None, username=None, user_id=None):
        # Simple authentication check without session access
        if not hasattr(request, 'user') or not request.user or request.user.is_anonymous:
            return redirect('history')
        
        # Check if user has required permissions
        if not (request.user.is_admin() or request.user.is_teacher()):
            messages.error(request, 'Access denied. Teacher or Admin privileges required.')
            return redirect('history')
        
        # Check edit permissions
        if username and user_id:
            try:
                target_user = User.objects.get(username__iexact=username, id=user_id)
                can_edit = (target_user == request.user) or request.user.is_admin()
                if not can_edit:
                    messages.error(request, 'You do not have permission to edit this data.')
                    return redirect('no_access')
            except User.DoesNotExist:
                return redirect('today')
        else:
            # Editing own data - always allowed
            can_edit = True
        if date:
            try:
                # Parse date from URL parameter (format: DD-MM-YY)
                today_date = datetime.strptime(date, '%d-%m-%y').date()
            except ValueError:
                # If date format is invalid, fall back to today
                from datetime import date as date_module
                today_date = date_module.today()
        else:
            from datetime import date as date_module
            today_date = date_module.today()
        
        today_weekday = today_date.weekday() + 1
        
        # Determine target user for data saving
        if username and user_id:
            try:
                target_user = User.objects.get(username__iexact=username, id=user_id)
            except User.DoesNotExist:
                target_user = request.user
        else:
            target_user = request.user
        
        # Get the specific subject being submitted
        subject_id = request.POST.get('subject_id')
        is_new_subject = request.POST.get('is_new_subject') == 'true'
        
        if not subject_id:
            messages.error(request, "No subject specified.")
            if date:
                if username and user_id:
                    return redirect('today_user_date', username=username, user_id=user_id, date=date)
                else:
                    return redirect('today_date', date=date)
            else:
                if username and user_id:
                    return redirect('today_user', username=username, user_id=user_id)
                else:
                    return redirect('today')
        
        # Handle new subject addition
        if is_new_subject and subject_id == 'new':
            new_subject_id = request.POST.get('new_subject_id')
            if not new_subject_id:
                messages.error(request, "Please select a subject to add.")
                if date:
                    if username and user_id:
                        return redirect('today_user_date', username=username, user_id=user_id, date=date)
                    else:
                        return redirect('today_date', date=date)
                else:
                    if username and user_id:
                        return redirect('today_user', username=username, user_id=user_id)
                    else:
                        return redirect('today')
            
            # Create a mock schedule for the new subject
            try:
                new_subject = Subject.objects.get(id=new_subject_id, created_by=target_user)
                subject_schedule = type('MockSchedule', (), {
                    'subject': new_subject,
                    'position': 999,  # High position for new subjects
                    'day_of_week': today_weekday,
                    'is_active': True,
                    'created_by': target_user
                })()
                subject_id = new_subject_id  # Update subject_id for processing
            except Subject.DoesNotExist:
                messages.error(request, "Selected subject not found.")
                if date:
                    if username and user_id:
                        return redirect('today_user_date', username=username, user_id=user_id, date=date)
                    else:
                        return redirect('today_date', date=date)
                else:
                    if username and user_id:
                        return redirect('today_user', username=username, user_id=user_id)
                    else:
                        return redirect('today')
        else:
            # Handle existing subject (original logic)
            # Get the original subject from the weekly schedule
            # If not found, create a mock schedule for any subject
            try:
                subject_schedule = WeeklySchedule.objects.get(
                    day_of_week=today_weekday,
                    subject_id=subject_id,
                    created_by=target_user
                )
            except WeeklySchedule.DoesNotExist:
                # Subject not in weekly schedule - create a mock schedule
                # This allows users to change any subject, not just weekly schedule subjects
                try:
                    subject = Subject.objects.get(id=subject_id, created_by=target_user)
                    subject_schedule = type('MockSchedule', (), {
                        'subject': subject,
                        'position': 999,  # High position for non-weekly subjects
                        'day_of_week': today_weekday,
                        'is_active': True,
                        'created_by': target_user
                    })()
                except Subject.DoesNotExist:
                    messages.error(request, "Subject not found.")
                    if date:
                        if username and user_id:
                            return redirect('today_user_date', username=username, user_id=user_id, date=date)
                        else:
                            return redirect('today_date', date=date)
                    else:
                        if username and user_id:
                            return redirect('today_user', username=username, user_id=user_id)
                        else:
                            return redirect('today')
        
        with transaction.atomic():
            # Note: We don't update the WeeklySchedule here to keep the weekly program intact
            # The subject change only affects the daily entry for this specific day
            new_subject_id = request.POST.get(f'subject_name_{subject_id}')
            if new_subject_id and int(new_subject_id) != subject_schedule.subject.id:
                try:
                    new_subject = Subject.objects.get(id=new_subject_id)
                    # We'll use the new subject for the daily entry, but keep the weekly schedule unchanged
                    daily_subject = new_subject
                except Subject.DoesNotExist:
                    daily_subject = subject_schedule.subject
            else:
                daily_subject = subject_schedule.subject
            
            # Get main entry data
            if is_new_subject:
                # For new subjects, use the 'new' suffix
                book_id = request.POST.get('book_new')
                pages = request.POST.get('pages_new')
                notes = request.POST.get('notes_new')
                important_notes = request.POST.get('important_notes_new')
            else:
                # For existing subjects, use the subject_id suffix
                book_id = request.POST.get(f'book_{subject_id}')
                pages = request.POST.get(f'pages_{subject_id}')
                notes = request.POST.get(f'notes_{subject_id}')
                important_notes = request.POST.get(f'important_notes_{subject_id}')
            
            # Check if there's any data for this subject (including homework and important notes)
            if is_new_subject:
                has_homework = any(
                    request.POST.get(f'homework_book_new_{i}') or 
                    request.POST.get(f'homework_pages_new_{i}')
                    for i in range(10)  # Check up to 10 homework entries
                )
            else:
                has_homework = any(
                request.POST.get(f'homework_book_{subject_id}_{i}') or 
                request.POST.get(f'homework_pages_{subject_id}_{i}')
                for i in range(10)  # Check up to 10 homework entries
            )
            
            if book_id or pages or notes or important_notes or has_homework:
                book = None
                if book_id:
                    try:
                        book = Book.objects.get(id=book_id)
                    except Book.DoesNotExist:
                        pass
                
                # If subject was changed, delete the old entry completely
                if new_subject_id and int(new_subject_id) != subject_schedule.subject.id:
                    # Delete any existing entry for the original subject and all related data
                    old_entries = DailyEntry.objects.filter(
                    date=today_date,
                    subject=subject_schedule.subject,
                        created_by=target_user
                    )
                    for old_entry in old_entries:
                        # Delete related DailyExtra and HomeworkEntry records
                        DailyExtra.objects.filter(daily_entry=old_entry).delete()
                        HomeworkEntry.objects.filter(daily_entry=old_entry).delete()
                        # Delete the main entry
                        old_entry.delete()
                
                # Get or create main entry for this subject (using daily_subject which may be different from weekly schedule)
                # Store the original weekly schedule subject ID for mapping purposes
                main_entry, created = DailyEntry.objects.get_or_create(
                    date=today_date,
                    subject=daily_subject,
                    defaults={
                        'book': book,
                        'pages': pages if pages else None,
                        'notes': notes if notes else None,
                        'important_notes': important_notes if important_notes else None,
                        'created_by': target_user
                    }
                )
                
                # Store the original weekly schedule subject ID in a custom field if it exists
                # This helps us map back to the weekly schedule position
                if hasattr(main_entry, 'original_weekly_subject_id'):
                    main_entry.original_weekly_subject_id = subject_schedule.subject.id
                    main_entry.save()
                
                # Update if not created
                if not created:
                    main_entry.book = book
                    main_entry.pages = pages if pages else None
                    main_entry.notes = notes if notes else None
                    main_entry.important_notes = important_notes if important_notes else None
                    main_entry.save()
                
                
                # Process extra entries for this subject
                # Clear existing extra entries for this subject
                main_entry.extras.all().delete()
                
                extra_count = 0
                while True:
                    if is_new_subject:
                        extra_book_id = request.POST.get(f'extra_book_new_{extra_count}')
                        extra_pages = request.POST.get(f'extra_pages_new_{extra_count}')
                    else:
                        extra_book_id = request.POST.get(f'extra_book_{subject_id}_{extra_count}')
                        extra_pages = request.POST.get(f'extra_pages_{subject_id}_{extra_count}')
                    
                    if not (extra_book_id or extra_pages):
                        break
                    
                    extra_book = None
                    if extra_book_id:
                        try:
                            extra_book = Book.objects.get(id=extra_book_id)
                        except Book.DoesNotExist:
                            pass
                    
                    DailyExtra.objects.create(
                        daily_entry=main_entry,
                        book=extra_book,
                        pages=extra_pages if extra_pages else None,
                        notes=None,  # No notes for extra entries
                        created_by=target_user
                    )
                    extra_count += 1
                
                # Process homework entries for this subject only if there's homework data
                if has_homework:
                    # Clear existing homework entries for this subject
                    main_entry.homework_entries.all().delete()
                    
                    homework_count = 0
                    while True:
                        if is_new_subject:
                            homework_book_id = request.POST.get(f'homework_book_new_{homework_count}')
                            homework_pages = request.POST.get(f'homework_pages_new_{homework_count}')
                        else:
                            homework_book_id = request.POST.get(f'homework_book_{subject_id}_{homework_count}')
                            homework_pages = request.POST.get(f'homework_pages_{subject_id}_{homework_count}')
                        
                        if not (homework_book_id or homework_pages):
                            break
                        
                        homework_book = None
                        if homework_book_id:
                            try:
                                homework_book = Book.objects.get(id=homework_book_id)
                            except Book.DoesNotExist:
                                pass
                        
                        HomeworkEntry.objects.create(
                            daily_entry=main_entry,
                            book=homework_book,
                            pages=homework_pages if homework_pages else None,
                            created_by=target_user
                        )
                        homework_count += 1
            else:
                # No data provided for this subject, delete any existing entry
                DailyEntry.objects.filter(
                    date=today_date,
                    subject=subject_schedule.subject
                ).delete()
        
        messages.success(request, "Today's entries saved successfully!")
        if date:
            if username and user_id:
                # Admin editing another user's data - redirect back to that user's page
                return redirect('today_user_date', username=username, user_id=user_id, date=date)
            else:
                # Editing own data
                return redirect('today_date', date=date)
        else:
            if username and user_id:
                # Admin editing another user's data - redirect back to that user's page
                return redirect('today_user', username=username, user_id=user_id)
            else:
                # Editing own data
                return redirect('today')


class HistoryView(View):
    def get(self, request, username, user_id, date=None):
        # Get the selected date for viewing daily data
        selected_date = None
        if date:
            # Date comes from URL path (format: DD-MM-YY)
            try:
                selected_date = datetime.strptime(date, '%d-%m-%y').date()
            except ValueError:
                selected_date = None
        else:
            # Check for date in query parameters (format: YYYY-MM-DD)
            date_param = request.GET.get('date')
            if date_param:
                try:
                    selected_date = datetime.strptime(date_param, '%Y-%m-%d').date()
                except ValueError:
                    selected_date = None
        
        # Get the target user (case insensitive)
        try:
            target_user = User.objects.get(username__iexact=username, id=user_id)
            
            # Security check: Allow viewing but track edit permissions
            # Users can view other users' calendars but only edit their own (unless admin)
            can_edit = False
            if request.user.is_authenticated:
                if target_user == request.user or request.user.is_admin():
                    can_edit = True
                
        except User.DoesNotExist:
            # If username doesn't exist or user_id doesn't match, show error
            messages.error(request, "User not found.")
            return redirect('home')
        
        # Get current month and year from URL parameters
        year_str = request.GET.get('year')
        month_str = request.GET.get('month')
        
        # Convert to integers if provided
        year = int(year_str) if year_str else None
        month = int(month_str) if month_str else None
        
        # If no year/month specified, use selected date's month/year or current date
        if not year or not month:
            if selected_date:
                # Use the selected date's month and year
                year = selected_date.year
                month = selected_date.month
            else:
                # Use current date as fallback
                from datetime import date as date_module
                today = date_module.today()
                year = today.year
                month = today.month
        
        # Generate calendar data
        cal_data = self.generate_calendar_data(year, month)
        
        # Get days with entries for highlighting
        days_with_entries = self.get_days_with_entries(year, month, target_user)
        
        # Get daily data if a date is selected
        daily_data = None
        if selected_date:
            daily_data = self.get_daily_data(selected_date, target_user)
        
        # Calculate previous and next month
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        
        template = 'mobile_history.html' if is_mobile_device(request) else 'history.html'
        return render(request, template, {
            'year': year,
            'month': month,
            'cal_data': cal_data,
            'days_with_entries': days_with_entries,
            'selected_date': selected_date,
            'daily_data': daily_data,
            'prev_month': prev_month,
            'prev_year': prev_year,
            'next_month': next_month,
            'next_year': next_year,
            'calendar': calendar,
            'target_user': target_user,
            'username': username,
            'user_id': user_id,
            'can_edit': can_edit
        })
    
    def generate_calendar_data(self, year, month):
        """Generate calendar data for the given month."""
        first_day = date_module(year, month, 1)
        last_day = date_module(year, month, calendar.monthrange(year, month)[1])
        
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
    
    def get_days_with_entries(self, year, month, target_user=None):
        """Get list of days that have entries for the given month."""
        first_day = date_module(year, month, 1)
        last_day = date_module(year, month, calendar.monthrange(year, month)[1])
        
        # Filter entries based on user role and target_user
        if target_user:
            # Anonymous user viewing specific user's data OR logged-in user viewing their own data
            entries = DailyEntry.objects.filter(
                date__gte=first_day,
                date__lte=last_day,
                created_by=target_user
            )
        elif not self.request.user.is_authenticated:
            # Anonymous users see no entries unless viewing specific user's data
            entries = DailyEntry.objects.none()
        elif self.request.user.is_admin():
            # Admin viewing their own history should only see their own entries
            entries = DailyEntry.objects.filter(
                date__gte=first_day,
                date__lte=last_day,
                created_by=self.request.user
            )
        else:  # Teacher - only their own entries
            entries = DailyEntry.objects.filter(
                date__gte=first_day,
                date__lte=last_day,
                created_by=self.request.user
            )
        
        return [entry.date.day for entry in entries]
    
    def get_daily_data(self, selected_date, target_user=None):
        """Get all daily data for the selected date in weekly schedule order."""
        # Get the target user for filtering
        if target_user:
            user_to_filter = target_user
        elif not self.request.user.is_authenticated:
            # Anonymous users see no entries unless viewing specific user's data
            return []
        elif self.request.user.is_admin():
            user_to_filter = self.request.user
        else:  # Teacher - only their own entries
            user_to_filter = self.request.user
        
        # Get weekly schedule for this day to maintain order
        weekly_schedules = WeeklySchedule.objects.filter(
            day_of_week=selected_date.weekday() + 1,
            is_active=True,
            subject__isnull=False,
            created_by=user_to_filter
        ).select_related('subject').order_by('position')
        
        daily_data = []
        
        # Go through weekly schedule in order
        weekly_subject_ids = set()
        for schedule in weekly_schedules:
            weekly_subject_ids.add(schedule.subject.id)
            # Try to find a daily entry for this subject and date
            try:
                daily_entry = DailyEntry.objects.get(
                    date=selected_date,
                    subject=schedule.subject,
                    created_by=user_to_filter
                )
                
                # Get extra entries for this main entry
                extras = DailyExtra.objects.filter(daily_entry=daily_entry).select_related('book')
                extra_books = []
                for extra in extras:
                    extra_books.append({
                        'book_name': extra.book.title if extra.book else "Unknown Book",
                        'pages': extra.pages,
                        'notes': extra.notes
                    })
                
                # Get homework entries for this main entry
                homework_entries = HomeworkEntry.objects.filter(daily_entry=daily_entry).select_related('book')
                homework_books = []
                for homework in homework_entries:
                    homework_books.append({
                        'book_name': homework.book.title if homework.book else "Unknown Book",
                        'pages': homework.pages
                    })
                
                daily_data.append({
                    'subject_name': daily_entry.subject.name,
                    'book_name': daily_entry.book.title if daily_entry.book else None,
                    'pages': daily_entry.pages,
                    'notes': daily_entry.notes,
                    'important_notes': daily_entry.important_notes,
                    'extras': extra_books,
                    'homework': homework_books,
                    'has_entry': True
                })
            except DailyEntry.DoesNotExist:
                # No daily entry for this subject, skip it
                continue
        
        # Add any daily entries that are NOT in the weekly schedule (new subjects)
        all_daily_entries = DailyEntry.objects.filter(
            date=selected_date,
            created_by=user_to_filter
        ).select_related('subject', 'book')
        
        for daily_entry in all_daily_entries:
            if daily_entry.subject.id not in weekly_subject_ids:
                # This is a new subject not in weekly schedule - add it at the end
                # Get extra entries for this main entry
                extras = DailyExtra.objects.filter(daily_entry=daily_entry).select_related('book')
                extra_books = []
                for extra in extras:
                    extra_books.append({
                        'book_name': extra.book.title if extra.book else "Unknown Book",
                        'pages': extra.pages,
                        'notes': extra.notes
                    })
                
                # Get homework entries for this main entry
                homework_entries = HomeworkEntry.objects.filter(daily_entry=daily_entry).select_related('book')
                homework_books = []
                for homework in homework_entries:
                    homework_books.append({
                        'book_name': homework.book.title if homework.book else "Unknown Book",
                        'pages': homework.pages
                    })
                
                daily_data.append({
                    'subject_name': daily_entry.subject.name,
                    'book_name': daily_entry.book.title if daily_entry.book else None,
                    'pages': daily_entry.pages,
                    'notes': daily_entry.notes,
                    'important_notes': daily_entry.important_notes,
                    'extras': extra_books,
                    'homework': homework_books,
                    'has_entry': True
                })
        
        return daily_data


class ExportPDFView(View):
    
    def get(self, request, date=None):
        from django.template.loader import render_to_string
        from .pdf_service import html_to_pdf_bytes
        
        # Parse the date
        if date:
            try:
                selected_date = datetime.strptime(date, '%d-%m-%y').date()
            except ValueError:
                messages.error(request, "Invalid date format")
                return redirect('history')
        else:
            selected_date = date_module.today()
        
        # Get daily data for the selected date
        daily_data = self.get_daily_data(selected_date)
        
        # Build HTML content from the same data structure
        html_content = self.build_html_content(daily_data, selected_date)
        
        # Render the print template
        html = render_to_string("print/tiptap_pdf.html", {"doc_html": html_content})
        base_url = request.build_absolute_uri("/")
        
        # Generate PDF using Playwright
        pdf_bytes = html_to_pdf_bytes(html, base_url=base_url)
        
        # Create response
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="school_organizer_{selected_date.strftime("%d_%m_%Y")}.pdf"'
        
        return response
    
    def build_html_content(self, daily_data, selected_date):
        """Build HTML content from daily data for Playwright PDF export"""
        html_parts = []
        
        # Title
        html_parts.append(f'<h1 style="text-align: center; font-size: 18px; margin-bottom: 10px;">{selected_date.strftime("%d %B %Y")}</h1>')
        
        # Check if there's any data
        has_data = any(entry['has_entry'] for entry in daily_data)
        
        if not has_data:
            html_parts.append('<p>No data saved for this day.</p>')
        else:
            # Add each subject's data
            for entry in daily_data:
                if entry['has_entry']:
                    # Subject title
                    html_parts.append(f'<h2 style="font-size: 16px; margin: 15px 0 8px 0;">{entry["subject_name"]}</h2>')
                    
                    # Start two-column layout
                    html_parts.append('<div class="subject-content">')
                    
                    # Left column: Resources and Notes
                    html_parts.append('<div class="left-column">')
                    
                    # Resources section
                    if entry['book_name'] or entry['extras']:
                        html_parts.append('<div class="section">')
                        html_parts.append('<div class="section-title">Ресурси:</div>')
                        
                        # Main book
                        if entry['book_name']:
                            resource_text = f"→ {entry['book_name']}"
                            if entry['pages']:
                                resource_text += f" стр. {entry['pages']}"
                            html_parts.append(f'<p>{resource_text}</p>')
                        
                        # Extra books
                        for extra in entry['extras']:
                            extra_text = f"→ {extra['book_name']}"
                            if extra['pages']:
                                extra_text += f" стр. {extra['pages']}"
                            html_parts.append(f'<p>{extra_text}</p>')
                        html_parts.append('</div>')
                    
                    # Notes
                    if entry['notes']:
                        html_parts.append('<div class="section">')
                        html_parts.append('<div class="section-title">Записки:</div>')
                        html_parts.append(entry['notes'])
                        html_parts.append('</div>')
                    
                    html_parts.append('</div>')  # End left column
                    
                    # Right column: Important Notes and Homework
                    html_parts.append('<div class="right-column">')
                    
                    # Important Notes
                    if entry.get('important_notes'):
                        html_parts.append('<div class="section">')
                        html_parts.append('<div class="section-title">Важно:</div>')
                        html_parts.append(entry['important_notes'])
                        html_parts.append('</div>')
                    
                    # Homework
                    if entry['homework']:
                        html_parts.append('<div class="section">')
                        html_parts.append('<div class="section-title">Домашно:</div>')
                        for hw in entry['homework']:
                            hw_text = f"→ {hw['book_name']}"
                            if hw['pages']:
                                hw_text += f" стр. {hw['pages']}"
                            html_parts.append(f'<p>{hw_text}</p>')
                        html_parts.append('</div>')
                    
                    html_parts.append('</div>')  # End right column
                    html_parts.append('</div>')  # End subject-content
        
        return ''.join(html_parts)
    
    def get_daily_data(self, selected_date):
        """Helper method to get daily data for PDF export"""
        # Get all subjects scheduled for this day (active schedules only)
        scheduled_subjects = WeeklySchedule.objects.filter(day_of_week=selected_date.weekday() + 1, is_active=True).select_related('subject').order_by('position')
        
        daily_data = []
        
        for schedule in scheduled_subjects:
            # Skip if schedule.subject is None
            if not schedule.subject:
                continue
                
            # Try to find an existing entry for this subject and date
            try:
                main_entry = DailyEntry.objects.get(date=selected_date, subject=schedule.subject)
                
                # Get extra entries
                extras = []
                for extra in main_entry.extras.all():
                    extras.append({
                        'book_name': extra.book.title if extra.book else 'No book selected',
                        'pages': extra.pages or ''
                    })
                
                # Get homework entries
                homework_books = []
                for hw in main_entry.homework_entries.all():
                    homework_books.append({
                        'book_name': hw.book.title if hw.book else 'No book selected',
                        'pages': hw.pages or ''
                    })
                
                daily_data.append({
                    'subject_name': schedule.subject.name,
                    'book_name': main_entry.book.title if main_entry.book else None,
                    'pages': main_entry.pages,
                    'notes': main_entry.notes,
                    'important_notes': main_entry.important_notes,
                    'extras': extras,
                    'homework': homework_books,
                    'has_entry': True
                })
            except DailyEntry.DoesNotExist:
                # No entry for this subject
                daily_data.append({
                    'subject_name': schedule.subject.name,
                    'book_name': None,
                    'pages': None,
                    'notes': None,
                    'important_notes': None,
                    'extras': [],
                    'homework': [],
                    'has_entry': False
                })
        
        return daily_data
    
    def convert_html_to_reportlab(self, html_content):
        """Convert HTML content to properly styled ReportLab flowable elements"""
        if not html_content:
            return []
        
        import re
        
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            # Fallback to basic text
            return [Paragraph(html_content.replace('<', '&lt;').replace('>', '&gt;'), 
                             ParagraphStyle('Normal', fontSize=10, fontName='Helvetica'))]
        
        # Parse HTML content with proper styling
        elements = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Define styles with proper inline formatting support
        normal_style = ParagraphStyle('Normal', fontSize=10, fontName='Helvetica')
        blockquote_style = ParagraphStyle(
            'Blockquote',
            fontSize=10,
            fontName='Helvetica',
            leftIndent=20,
            rightIndent=20,
            spaceBefore=6,
            spaceAfter=6,
            maxWidth=2.4*inch  # Same as table width
        )
        
        # Process elements in order with proper ReportLab components
        for element in soup.find_all(['p', 'div', 'table', 'ul', 'ol', 'blockquote', 'hr', 'pre', 'code'], recursive=False):
            if element.name == 'table':
                # Create proper table with borders and styling
                table_element = self.create_reportlab_table(element)
                if table_element:
                    elements.append(Spacer(1, 8))
                    elements.append(table_element)
                    elements.append(Spacer(1, 12))
                element.decompose()
            elif element.name == 'ul':
                # Check if this is a checklist using robust detection
                if self.is_tasklist_ul(element):
                    elements.append(Spacer(1, 4))
                    elements.append(self.create_checklist(element, normal_style))
                    elements.append(Spacer(1, 8))
                else:
                    # Regular unordered list
                    elements.append(Spacer(1, 4))
                    elements.append(self.create_unordered_list(element, normal_style))
                    elements.append(Spacer(1, 8))
                element.decompose()
            elif element.name == 'ol':
                # Create ordered list with proper numbering
                elements.append(Spacer(1, 4))
                elements.append(self.create_ordered_list(element, normal_style))
                elements.append(Spacer(1, 8))
                element.decompose()
            elif element.name == 'blockquote':
                # Process blockquote with styled table rendering
                content_width = 5*inch  # Default content width
                elements.append(Spacer(0, 6))
                elements.append(self.create_blockquote(element, normal_style, content_width))
                elements.append(Spacer(0, 6))
                element.decompose()
            elif element.name == 'hr':
                # Create horizontal rule
                hr_table = Table([['']], colWidths=[2.4*inch])
                hr_style = TableStyle([
                    ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#888888')),
                    ('PADDING', (0, 0), (-1, -1), 6, 6)
                ])
                hr_table.setStyle(hr_style)
                elements.append(Spacer(1, 8))
                elements.append(hr_table)
                elements.append(Spacer(1, 8))
            elif element.name in ['pre', 'code']:
                # Handle code blocks
                code_text = element.get_text()
                code_para = Paragraph(f'<font name="Courier">{code_text}</font>', normal_style)
                elements.append(Spacer(1, 4))
                elements.append(code_para)
                elements.append(Spacer(1, 8))
            else:
                # top-level container with checkboxes (not a UL/OL)
                if element.name not in ('ul','ol') and element.find('input', {'type':'checkbox'}):
                    cl = self.create_checklist_from_container(element, normal_style)
                    if cl:
                        elements.append(cl)
                        element.decompose()
                        continue
                # Handle paragraphs and divs with inline styles
                text_content = self.extract_text_with_inline_styles(element)
                if text_content.strip():
                    elements.append(Paragraph(text_content, normal_style))
        
        return elements
    
    def create_list_items(self, list_element, ordered=False):
        """Create ListItem objects for ReportLab ListFlowable"""
        from reportlab.platypus import ListItem
        
        items = []
        list_items = list_element.find_all('li')
        
        for idx, item in enumerate(list_items, 1):
            # Check for checkbox first
            checkbox = item.find('input', {'type': 'checkbox'})
            
            if checkbox:
                # This is a checklist item
                checked = checkbox.has_attr('checked') or checkbox.get('checked') is not None
                prefix = "[x]" if checked else "[_]"
                
                # Get text content without the checkbox element
                checkbox.decompose()  # Remove checkbox from the item
                text_content = self.extract_text_with_inline_styles(item)
                text_content = text_content.strip()
                
                if text_content:
                    items.append(ListItem(Paragraph(f"{prefix} {text_content}", 
                        ParagraphStyle('ListItem', fontSize=10, fontName='Helvetica'))))
            else:
                # Regular list item (bullet or numbered)
                text_content = self.extract_text_with_inline_styles(item)
                text_content = text_content.strip()
                
                if text_content:
                    if ordered:
                        # Numbered list - ReportLab will handle numbering automatically
                        items.append(ListItem(Paragraph(text_content, 
                            ParagraphStyle('ListItem', fontSize=10, fontName='Helvetica'))))
                    else:
                        # Bullet list - ReportLab will handle bullets automatically
                        items.append(ListItem(Paragraph(text_content, 
                            ParagraphStyle('ListItem', fontSize=10, fontName='Helvetica'))))
        
        return items

    def create_checklist_from_container(self, container, style):
        """Top-level "free text" task items (checkboxes not wrapped in <ul>)"""
        cbs = container.find_all('input', {'type': 'checkbox'})
        if not cbs: return None
        items = []
        for cb in cbs:
            checked = cb.has_attr('checked') or cb.get('checked') is not None
            # capture label until the next checkbox sibling
            node, parts = cb.next_sibling, []
            while node and not (getattr(node, 'name', None) == 'input' and node.get('type') == 'checkbox'):
                parts.append(str(node)); node = node.next_sibling
            frag = ''.join(parts).strip() or str(cb.parent)
            # strip any inputs from the fragment
            from bs4 import BeautifulSoup
            frag_soup = BeautifulSoup(frag, 'html.parser')
            for ip in frag_soup.find_all('input', {'type':'checkbox'}): ip.decompose()
            for lab in frag_soup.find_all('label'): lab.unwrap()
            label = self.extract_text_with_inline_styles(frag_soup)
            items.append(ListItem(Paragraph(label, style), bulletText='[x]' if checked else '[_]'))
        return ListFlowable(
            items,
            bulletType='bullet',
            leftIndent=self.LIST_LEFT, bulletIndent=self.LIST_BULLET,
            bulletFontName=self.LIST_FONT, bulletFontSize=self.LIST_SIZE,
        )

    def create_checklist(self, ul, style):
        from reportlab.platypus import ListFlowable, ListItem, Paragraph
        
        lis = ul.find_all('li', recursive=False)
        items = []
        for li in lis:
            cb = li.find('input', {'type': 'checkbox'})
            checked = bool(cb and (cb.has_attr('checked') or cb.get('checked') is not None))
            if cb: cb.decompose()
            for lab in li.find_all('label', recursive=False): lab.unwrap()
            label = self.extract_text_with_inline_styles(li)
            items.append(ListItem(Paragraph(label, style), bulletText='[x]' if checked else '[_]'))
        return ListFlowable(
            items,
            bulletType='bullet',
            leftIndent=self.LIST_LEFT, bulletIndent=self.LIST_BULLET,
            bulletFontName=self.LIST_FONT, bulletFontSize=self.LIST_SIZE,
        )
    
    def create_unordered_list(self, ul, style):
        from reportlab.platypus import ListFlowable, ListItem, Paragraph
        
        lis = ul.find_all('li', recursive=False)
        items = []
        for li in lis:
            label = self.extract_text_with_inline_styles(li)
            items.append(ListItem(Paragraph(label, style), bulletText='•'))
        return ListFlowable(
            items,
            bulletType='bullet',
            leftIndent=self.LIST_LEFT,
            bulletIndent=self.LIST_BULLET,
            bulletFontName=self.LIST_FONT,
            bulletFontSize=self.LIST_SIZE,
        )
    
    def create_ordered_list(self, ol, style):
        from reportlab.platypus import ListFlowable, ListItem, Paragraph
        
        lis = ol.find_all('li', recursive=False)
        items = []
        for i, li in enumerate(lis, 1):
            label = self.extract_text_with_inline_styles(li)
            items.append(ListItem(Paragraph(label, style), bulletText=f'{i}.'))
        return ListFlowable(
            items,
            bulletType='bullet',  # we supply the numbers ourselves
            leftIndent=self.LIST_LEFT, bulletIndent=self.LIST_BULLET,
            bulletFontName=self.LIST_FONT, bulletFontSize=self.LIST_SIZE,
        )
    
    def create_blockquote(self, blockquote_tag, style, content_width):
        from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        
        # build the cell like a table cell: preserve order + styles
        cell = []
        from bs4.element import NavigableString, Tag
        for child in blockquote_tag.children:
            if isinstance(child, NavigableString):
                txt = str(child).strip()
                if txt:
                    cell.append(Paragraph(self.extract_text_with_inline_styles(child), style))
            elif isinstance(child, Tag):
                if child.name == 'ul':
                    cell.append(self.create_checklist(child, style) if self.is_tasklist_ul(child)
                                else self.create_unordered_list(child, style))
                elif child.name == 'ol':
                    cell.append(self.create_ordered_list(child, style))
                else:
                    # if this child contains checkboxes but isn't a UL, render as checklist container
                    if child.find('input', {'type':'checkbox'}):
                        cl = self.create_checklist_from_container(child, style)
                        if cl: cell.append(cl)
                    elif child.name in ('p','span','b','i','u','strong','em'):
                        cell.append(Paragraph(self.extract_text_with_inline_styles(child), style))

        tbl = Table([[cell]], colWidths=[self.TABLE_TOTAL_WIDTH + self.QUOTE_EXTRA_PTS])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        return tbl
    
    def render_cell(self, cell, style):
        """Order-preserving cell renderer that maintains DOM order"""
        from bs4.element import NavigableString, Tag
        from reportlab.platypus import Paragraph, ListFlowable, ListItem
        
        items = []
        for child in cell.children:
            if isinstance(child, NavigableString):
                txt = str(child).strip()
                if txt:
                    items.append(Paragraph(self.format_inline_styles_safe(txt), style))
            elif isinstance(child, Tag):
                name = child.name
                if name in ('p', 'span', 'b', 'i', 'u', 'strong', 'em'):
                    items.append(Paragraph(self.format_inline_styles_safe(str(child)), style))
                elif name == 'ul':
                    if self.is_tasklist_ul(child):
                        items.append(self.create_checklist(child, style))
                    else:
                        items.append(self.create_unordered_list(child, style))
                elif name == 'ol':
                    items.append(self.create_ordered_list(child, style))
        
        if not items:
            items.append(Paragraph('&nbsp;', style))
        
        return items
    
    def extract_text_with_inline_styles(self, element):
        """Extract text content while preserving inline styles for ReportLab"""
        if not element:
            return ""
        
        # Build text with proper inline styling tags
        result = ""
        
        def process_node(node):
            nonlocal result
            # Check if this is a Tag object (has name attribute) or NavigableString
            if hasattr(node, 'name') and node.name is not None:
                # This is a Tag object with children
                if node.name in ['b', 'strong']:
                    result += "<b>"
                    for child in node.children:
                        process_node(child)
                    result += "</b>"
                elif node.name in ['i', 'em']:
                    result += "<i>"
                    for child in node.children:
                        process_node(child)
                    result += "</i>"
                elif node.name == 'u':
                    result += "<u>"
                    for child in node.children:
                        process_node(child)
                    result += "</u>"
                elif node.name in ['input', 'br']:
                    # Skip these tags
                    pass
                else:
                    # For other tags, process children if they exist
                    if hasattr(node, 'children'):
                        for child in node.children:
                            process_node(child)
            else:
                # This is a NavigableString (text node) or other object
                result += str(node)
        
        # Process the element - check if it has children attribute
        if hasattr(element, 'children'):
            for child in element.children:
                process_node(child)
        else:
            # If no children, it's likely a text node
            result = str(element)
        
        # If no result, get plain text
        if not result.strip():
            result = element.get_text().strip() if hasattr(element, 'get_text') else str(element)
        
        return result
    
    def html_to_plain_text(self, html_content):
        """Convert HTML to plain text with basic formatting markers - completely safe for ReportLab"""
        if not html_content:
            return ""
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text_parts = []
            
            # Process each element
            for element in soup.find_all(['p', 'div', 'table', 'ul', 'ol', 'blockquote', 'hr', 'pre', 'code'], recursive=False):
                if element.name == 'table':
                    # Handle tables
                    rows = element.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        row_text = []
                        for cell in cells:
                            cell_text = cell.get_text().strip()
                            if cell_text:
                                row_text.append(cell_text)
                        if row_text:
                            text_parts.append(" | ".join(row_text))
                
                elif element.name in ['ul', 'ol']:
                    # Handle lists
                    items = element.find_all('li')
                    for i, item in enumerate(items):
                        item_text = item.get_text().strip()
                        if item_text:
                            if element.name == 'ol':
                                text_parts.append(f"{i+1}. {item_text}")
                            else:
                                # Check for checkbox
                                checkbox = item.find('input', {'type': 'checkbox'})
                                if checkbox:
                                    checked = checkbox.has_attr('checked') or checkbox.get('checked') is not None
                                    prefix = "[x]" if checked else "[_]"   # ASCII checkboxes
                                    text_parts.append(f"{prefix} {item_text}")
                                else:
                                    text_parts.append(f"• {item_text}")
                
                elif element.name == 'blockquote':
                    # Handle blockquotes
                    quote_text = element.get_text().strip()
                    if quote_text:
                        text_parts.append(f"> {quote_text}")
                
                elif element.name == 'hr':
                    # Handle horizontal rules
                    text_parts.append("---")
                
                else:
                    # Handle other elements
                    element_text = element.get_text().strip()
                    if element_text:
                        text_parts.append(element_text)
            
            # If no structured elements found, get all text
            if not text_parts:
                all_text = soup.get_text().strip()
                if all_text:
                    text_parts.append(all_text)
            
            return "\n".join(text_parts)
            
        except Exception as e:
            # If anything goes wrong, return a safe fallback
            print(f"Error in html_to_plain_text: {e}")
            return "Content could not be processed"
    
    def create_reportlab_table(self, table_element):
        """Create a ReportLab table with proper borders and styling"""
        try:
            rows = table_element.find_all('tr')
            if not rows:
                return None
            
            # Extract table data
            table_data = []
            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_data = []
                for cell in cells:
                    # Use new order-preserving cell renderer
                    normal_style = ParagraphStyle('TableCell', fontSize=10, leading=12, leftIndent=0, fontName='Helvetica')
                    cell_content = self.render_cell(cell, normal_style)
                    row_data.append(cell_content)
                table_data.append(row_data)
            
            # Create table with proper column widths
            table = Table(table_data, colWidths=self.TABLE_COL_WIDTHS)
            
            # Apply table styling
            table_style = TableStyle([
                # Grid lines - subtle gray
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e0e0e0')),
                # Header row styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                # Cell padding
                ('PADDING', (0, 0), (-1, -1), 8, 8),
                    # Text alignment
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    # Minimum row height
                    ('MINROWHEIGHT', (0, 0), (-1, -1), 18),
                ])
            
            table.setStyle(table_style)
            return table
            
        except Exception as e:
            print(f"Error creating table: {e}")
            return None
            rows = table_element.find_all('tr')
            if not rows:
                return None
            
            table_data = []
            
            for i, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                if cells:
                    row_data = []
                    for cell in cells:
                        cell_content = self.format_cell_content_advanced(cell)
                        # Ensure we always have content, even if empty
                        if not cell_content or cell_content.strip() == '':
                            cell_content = ' '
                        row_data.append(cell_content)
                    table_data.append(row_data)
                else:
                    # Handle empty rows - add empty row to maintain table structure
                    table_data.append([' ', ' ', ' '])
            
            if table_data:
                # Create table with much narrower width
                # Make table very narrow - only about 2.5 inches total
                table = Table(table_data, colWidths=[0.8*inch, 0.8*inch, 0.8*inch])  # Very narrow table (2.4 inches total)
                table.setStyle(TableStyle([
                    # Header row styling (first row)
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),  # Light gray like quotes
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                    
                    # All rows styling
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e0e0e0')),  # Very thin subtle gray borders
                    ('PADDING', (0, 0), (-1, -1), 6),  # Reduced padding
                    
                    # Data rows alignment (not header)
                    ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 1), (-1, -1), 'TOP'),
                ]))
                return table
        except Exception as e:
            print(f"Error creating table: {e}")
        
        return None
    
    def format_cell_content(self, cell):
        """Format content within table cells as Paragraph objects"""
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import Paragraph
        
        normal_style = ParagraphStyle('TableCell', fontSize=10, leading=12, leftIndent=0, fontName='Helvetica')
        
        lists = cell.find_all(['ul', 'ol'])
        lines = []
        
        if lists:
            for list_elem in lists:
                items = list_elem.find_all('li')
                for j, item in enumerate(items):
                    text = item.get_text().strip()
                    if list_elem.name == 'ol':
                        prefix = f"{j+1}."
                    else:
                        checkbox = item.find('input', {'type': 'checkbox'})
                        if checkbox:
                            checked = checkbox.has_attr('checked') or checkbox.get('checked') is not None
                            prefix = "[x]" if checked else "[_]"   # ASCII checkboxes
                        else:
                            prefix = "-"   # plain dash for bullets
                    lines.append(f"{prefix} {text}")
        else:
            text = cell.get_text().strip()
            if text:
                lines.append(text)
        
        return Paragraph("<br/>".join(lines), normal_style)
    
    def format_cell_content_advanced(self, cell):
        """Format content within table cells as Paragraph objects with proper list handling"""
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import Paragraph
        
        normal_style = ParagraphStyle('TableCell', fontSize=10, leading=12, leftIndent=0, fontName='Helvetica')
        
        # Check if cell has any content
        cell_content = cell.get_text(strip=True)
        if not cell_content:
            # Return non-breaking space for empty cells to maintain row height
            return Paragraph(" ", normal_style)
        
        # Check if cell contains lists
        lists = cell.find_all(['ul', 'ol'])
        if lists:
            # Handle lists in table cells - each list item gets its own line
            lines = []
            for list_elem in lists:
                items = list_elem.find_all('li')
                for item in items:
                    # Check for checkbox
                    checkbox = item.find('input', {'type': 'checkbox'})
                    if checkbox:
                        checked = checkbox.has_attr('checked') or checkbox.get('checked') is not None
                        prefix = "[x]" if checked else "[_]"
                        checkbox.decompose()  # Remove checkbox
                        text_content = self.extract_text_with_inline_styles(item)
                        text_content = text_content.strip()
                        if text_content:
                            lines.append(f"{prefix} {text_content}")
                    else:
                        # Regular list item
                        text_content = self.extract_text_with_inline_styles(item)
                        text_content = text_content.strip()
                        if text_content:
                            lines.append(f"• {text_content}")
            
            # Also get any non-list content with inline styles preserved
            for element in cell.children:
                if hasattr(element, 'name') and element.name not in ['ul', 'ol']:
                    text_content = self.extract_text_with_inline_styles(element)
                    if text_content.strip():
                        lines.append(text_content)
            
            if lines:
                return Paragraph("<br/>".join(lines), normal_style)
        
        # Extract text content with inline styles preserved for regular content
        text_content = self.extract_text_with_inline_styles(cell)
        
        # If no content, return non-breaking space
        if not text_content.strip():
            return Paragraph(" ", normal_style)
        
        # Return Paragraph object with proper styling and inline formatting
        return Paragraph(text_content, normal_style)
    
    def extract_text_with_formatting(self, element):
        """Extract text content while preserving inline formatting tags"""
        if not element:
            return ""
        
        # Get all text nodes and their formatting from the element
        formatted_text = ""
        
        # Process each child element
        for child in element.children:
            if hasattr(child, 'name'):
                # This is a tag
                if child.name in ['b', 'strong']:
                    formatted_text += f"<b>{child.get_text()}</b>"
                elif child.name in ['i', 'em']:
                    formatted_text += f"<i>{child.get_text()}</i>"
                elif child.name == 'u':
                    formatted_text += f"<u>{child.get_text()}</u>"
                elif child.name in ['input', 'br']:
                    # Skip these tags
                    continue
                else:
                    # For other tags, just get the text
                    formatted_text += child.get_text()
            else:
                # This is a text node
                formatted_text += str(child)
        
        # If no formatted text found, get plain text
        if not formatted_text.strip():
            formatted_text = element.get_text().strip()
        
        return formatted_text
    
    def format_inline_styles_safe(self, text):
        """Format inline styles with enhanced safety for ReportLab paraparser"""
        import re
        
        if not text:
            return ""
        
        # For maximum safety, remove all HTML tags and return plain text
        # This prevents any HTML parsing errors in ReportLab
        text = re.sub(r'<[^>]*>', '', text)
        return text.strip()
        
        # Handle italic text - ensure proper tag matching
        text = re.sub(r'<i>(.*?)</i>', r'<i>\1</i>', text)
        text = re.sub(r'<em>(.*?)</em>', r'<i>\1</i>', text)
        # Handle unclosed italic tags
        text = re.sub(r'<i>([^<]*)', r'<i>\1</i>', text)
        text = re.sub(r'<em>([^<]*)', r'<i>\1</i>', text)
        
        # Handle underline - ensure proper tag matching
        text = re.sub(r'<u>(.*?)</u>', r'<u>\1</u>', text)
        # Handle unclosed underline tags
        text = re.sub(r'<u>([^<]*)', r'<u>\1</u>', text)
        
        # Handle strike-through - ensure proper tag matching
        text = re.sub(r'<s>(.*?)</s>', r'<s>\1</s>', text)
        text = re.sub(r'<strike>(.*?)</strike>', r'<s>\1</s>', text)
        # Handle unclosed strike tags
        text = re.sub(r'<s>([^<]*)', r'<s>\1</s>', text)
        text = re.sub(r'<strike>([^<]*)', r'<s>\1</s>', text)
        
        # Remove any remaining problematic HTML tags
        text = re.sub(r'<[^>]*$', '', text)  # Remove unclosed tags at end
        text = re.sub(r'^[^<]*>', '', text)  # Remove orphaned closing tags at start
        
        # Clean up any remaining HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        
        return text
    
    def create_reportlab_list(self, list_element):
        """Create ReportLab list items from HTML list element with proper Tiptap support"""
        elements = []
        items = list_element.find_all('li')

        for i, item in enumerate(items):
            # Check for checkbox first before processing text
            checkbox = item.find('input', {'type': 'checkbox'})
            
            if list_element.name == 'ol':
                # Ordered list - use numbers
                # Get text content while preserving inline formatting
                text_content = self.extract_text_with_formatting(item)
                text = self.format_inline_styles(text_content) if text_content else ""
                prefix = f"{i+1}."
            else:
                # Unordered list - check for checkbox
                if checkbox:
                    # Checklist item - check if checked
                    checked = checkbox.has_attr('checked') or checkbox.get('checked') is not None
                    prefix = "[x]" if checked else "[_]"
                    # Get text content while preserving inline formatting
                    text_content = self.extract_text_with_formatting(item)
                    text = self.format_inline_styles(text_content) if text_content else ""
                else:
                    # Regular bullet list
                    prefix = "-"   # plain dash for bullets
                    # Get text content while preserving inline formatting
                    text_content = self.extract_text_with_formatting(item)
                    text = self.format_inline_styles(text_content) if text_content else ""

            # Create paragraph with proper indentation
            elements.append(Paragraph(f"{prefix} {text}", 
                ParagraphStyle('ListItem', fontSize=10, fontName='Helvetica', leftIndent=20)))

        return elements
    
    def format_inline_styles(self, html_text):
        """Format inline styles (bold, italic, underline, hyperlinks) with proper HTML cleaning"""
        import re
        
        # First, clean up any malformed HTML by removing unclosed tags
        # Remove any tags that don't have proper closing tags
        html_text = re.sub(r'<([^>]*?)(?<!/)>', lambda m: m.group(0) if m.group(1).strip() else '', html_text)
        
        # Handle hyperlinks first (before removing other tags)
        html_text = re.sub(r'<a[^>]*href=[\'"]([^\'"]*)[\'"][^>]*>([^<]*)</a>', r'<link href="\1" color="blue"><u>\2</u></link>', html_text)
        
        # Bold - ensure proper tag matching and handle unclosed tags
        html_text = re.sub(r'<(strong|b)>([^<]*)</(strong|b)>', r'<b>\2</b>', html_text)
        html_text = re.sub(r'<(strong|b)>([^<]*)', r'<b>\2</b>', html_text)  # Handle unclosed tags
        
        # Italic - ensure proper tag matching and handle unclosed tags
        html_text = re.sub(r'<(em|i)>([^<]*)</(em|i)>', r'<i>\2</i>', html_text)
        html_text = re.sub(r'<(em|i)>([^<]*)', r'<i>\2</i>', html_text)  # Handle unclosed tags
        
        # Underline - ensure proper tag matching and handle unclosed tags
        html_text = re.sub(r'<u>([^<]*)</u>', r'<u>\1</u>', html_text)
        html_text = re.sub(r'<u>([^<]*)', r'<u>\1</u>', html_text)  # Handle unclosed tags
        
        # Strike through - ensure proper tag matching and handle unclosed tags
        html_text = re.sub(r'<(s|strike)>([^<]*)</(s|strike)>', r'<strike>\2</strike>', html_text)
        html_text = re.sub(r'<(s|strike)>([^<]*)', r'<strike>\2</strike>', html_text)  # Handle unclosed tags
        
        # Remove other HTML tags but preserve ReportLab formatting
        html_text = re.sub(r'<(?![/]?(?:b|i|u|strike|link))[^>]+>', '', html_text)
        
        # Remove any remaining unclosed HTML tags to prevent paraparser errors
        html_text = re.sub(r'<[^>]*$', '', html_text)  # Remove tags at end of string
        html_text = re.sub(r'^[^<]*>', '', html_text)  # Remove orphaned closing tags at start
        
        # Clean up any remaining HTML entities and tags
        html_text = html_text.replace('&nbsp;', ' ')
        html_text = html_text.replace('&amp;', '&')
        html_text = html_text.replace('&lt;', '<')
        html_text = html_text.replace('&gt;', '>')
        
        return html_text
    
    def html_to_image(self, html_content):
        """Convert HTML content to an image for PDF embedding"""
        if not html_content:
            return None
        
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            import tempfile
            import time
            
            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                # Create a complete HTML document with CSS styling
                html_doc = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            font-size: 14px;
                            line-height: 1.4;
                            margin: 20px;
                            background: white;
                            color: black;
                            width: 600px;
                        }}
                        table {{
                            border-collapse: collapse;
                            width: 100%;
                            margin: 10px 0;
                        }}
                        table, th, td {{
                            border: 1px solid #ddd;
                        }}
                        th, td {{
                            padding: 8px;
                            text-align: left;
                        }}
                        th {{
                            background-color: #f2f2f2;
                            font-weight: bold;
                        }}
                        ul, ol {{
                            margin: 10px 0;
                            padding-left: 20px;
                        }}
                        li {{
                            margin: 5px 0;
                        }}
                        blockquote {{
                            margin: 10px 0;
                            padding: 10px 20px;
                            background: #f8f9fa;
                            font-style: italic;
                            border-left: 4px solid #6c757d;
                        }}
                        hr {{
                            border: none;
                            border-top: 1px solid #e0e0e0;
                            margin: 15px 0;
                        }}
                        .checklist-item {{
                            margin: 5px 0;
                        }}
                        .checklist-item input[type="checkbox"] {{
                            margin-right: 8px;
                        }}
                    </style>
                </head>
                <body>
                    {html_content}
                </body>
                </html>
                """
                f.write(html_doc)
                temp_html_file = f.name
            
            # Set up Chrome options for headless browsing
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=800,600')
            
            # Create WebDriver
            driver = webdriver.Chrome(options=chrome_options)
            
            try:
                # Load the HTML file
                driver.get(f'file://{temp_html_file}')
                time.sleep(2)  # Wait for content to load
                
                # Get the body element
                body = driver.find_element(By.TAG_NAME, 'body')
                
                # Take screenshot of the body
                screenshot = body.screenshot_as_png
                
                # Convert to PIL Image
                img = PILImage.open(BytesIO(screenshot))
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as img_file:
                    img.save(img_file.name, 'PNG')
                    return img_file.name
                    
            finally:
                driver.quit()
                os.unlink(temp_html_file)
                
        except Exception as e:
            print(f"Error creating image from HTML: {e}")
            return None

class ExportJPEGView(View):
    def get(self, request, date=None):
        from django.template.loader import render_to_string
        from .pdf_service import get_browser
        
        # Parse the date
        if date:
            try:
                selected_date = datetime.strptime(date, "%d-%m-%y").date()
            except ValueError:
                messages.error(request, "Invalid date format")
                return redirect("history")
        else:
            selected_date = date_module.today()
        
        # Get daily data for the selected date
        daily_data = self.get_daily_data(selected_date, request)
        
        # Build HTML content using the same template as PDF export
        html_content = self.build_html_content(daily_data, selected_date)
        
        # Render the template
        doc_html = render_to_string('print/tiptap_pdf.html', {'doc_html': html_content})
        
        try:
            # Use Playwright to generate JPEG
            browser = get_browser()
            page = browser.new_page()
            
            try:
                # Set content directly - no external resources needed for our use case
                page.set_content(doc_html, wait_until="load")
                
                # Take screenshot as JPEG
                jpeg_bytes = page.screenshot(
                    type='jpeg',
                    quality=95,
                    full_page=True
                )
                
                # Create JPEG response
                response = HttpResponse(jpeg_bytes, content_type='image/jpeg')
                response['Content-Disposition'] = f'attachment; filename="school_organizer_{selected_date.strftime("%d_%m_%Y")}.jpg"'
                
                return response
                
            finally:
                page.close()
                
        except Exception as e:
            # Fallback: return error message
            messages.error(request, f"Error generating JPEG: {str(e)}")
            return redirect("history")
    
    def get_daily_data(self, selected_date, request):
        """Helper method to get daily data for JPEG export"""
        # Get all subjects scheduled for this day (active schedules only)
        scheduled_subjects = WeeklySchedule.objects.filter(day_of_week=selected_date.weekday() + 1, is_active=True).select_related("subject").order_by("position")
        
        daily_data = []
        
        for schedule in scheduled_subjects:
            # Check if user has access to this subject
            if schedule.subject and schedule.subject.created_by == request.user:
                # Get daily entry for this subject and date
                daily_entry = DailyEntry.objects.filter(
                    subject=schedule.subject,
                    date=selected_date,
                    created_by=request.user
                ).first()
                
                has_entry = daily_entry is not None
                
                # Get book information
                book_name = ""
                pages = ""
                if daily_entry and daily_entry.book:
                    book_name = daily_entry.book.title
                    pages = daily_entry.pages or ""
                
                # Get extras
                extras = []
                if daily_entry:
                    for extra in daily_entry.extras.all():
                        extra_data = {
                            'book_name': extra.book.title if extra.book else "",
                            'pages': extra.pages or ""
                        }
                        extras.append(extra_data)
                
                # Get homework
                homework = []
                if daily_entry:
                    for hw in daily_entry.homework_entries.all():
                        hw_data = {
                            'book_name': hw.book.title if hw.book else "",
                            'pages': hw.pages or ""
                        }
                        homework.append(hw_data)
                
                # Get notes and important notes
                notes = daily_entry.notes if daily_entry else ""
                important_notes = daily_entry.important_notes if daily_entry else ""
                
                daily_data.append({
                    'subject_name': schedule.subject.name,
                    'has_entry': has_entry,
                    'book_name': book_name,
                    'pages': pages,
                    'extras': extras,
                    'homework': homework,
                    'notes': notes,
                    'important_notes': important_notes,
                    'created_by': schedule.created_by
                })
        
        return daily_data
    
    def build_html_content(self, daily_data, selected_date):
        """Build HTML content from daily data for JPEG export (only Ресурси, Важно, Домашно)"""
        html_parts = []
        
        # Title
        html_parts.append(f'<h1 style="text-align: center; font-size: 18px; margin-bottom: 10px;">{selected_date.strftime("%d %B %Y")}</h1>')
        
        # Check if there's any data
        has_data = any(entry['has_entry'] for entry in daily_data)
        
        if not has_data:
            html_parts.append('<p>No data saved for this day.</p>')
        else:
            # Add each subject's data
            for entry in daily_data:
                if entry['has_entry']:
                    # Subject title
                    html_parts.append(f'<h2 style="font-size: 16px; margin: 15px 0 8px 0;">{entry["subject_name"]}</h2>')
                    
                    # Start two-column layout
                    html_parts.append('<div class="subject-content">')
                    
                    # Left column: Resources only (no Notes for JPEG)
                    html_parts.append('<div class="left-column">')
                    
                    # Resources section
                    if entry['book_name'] or entry['extras']:
                        html_parts.append('<div class="section">')
                        html_parts.append('<div class="section-title">Ресурси:</div>')
                        
                        # Main book
                        if entry['book_name']:
                            resource_text = f"→ {entry['book_name']}"
                            if entry['pages']:
                                resource_text += f" стр. {entry['pages']}"
                            html_parts.append(f'<p>{resource_text}</p>')
                        
                        # Extra books
                        for extra in entry['extras']:
                            extra_text = f"→ {extra['book_name']}"
                            if extra['pages']:
                                extra_text += f" стр. {extra['pages']}"
                            html_parts.append(f'<p>{extra_text}</p>')
                        html_parts.append('</div>')
                    
                    # Notes - SKIPPED for JPEG export (only show Ресурси, Важно, Домашно)
                    # if entry['notes']:
                    #     html_parts.append('<div class="section">')
                    #     html_parts.append('<div class="section-title">Записки:</div>')
                    #     html_parts.append(entry['notes'])
                    #     html_parts.append('</div>')
                    
                    html_parts.append('</div>')  # End left column
                    
                    # Right column: Important Notes and Homework
                    html_parts.append('<div class="right-column">')
                    
                    # Important Notes
                    if entry.get('important_notes'):
                        html_parts.append('<div class="section">')
                        html_parts.append('<div class="section-title">Важно:</div>')
                        html_parts.append(entry['important_notes'])
                        html_parts.append('</div>')
                    
                    # Homework
                    if entry['homework']:
                        html_parts.append('<div class="section">')
                        html_parts.append('<div class="section-title">Домашно:</div>')
                        for hw in entry['homework']:
                            hw_text = f"→ {hw['book_name']}"
                            if hw['pages']:
                                hw_text += f" стр. {hw['pages']}"
                            html_parts.append(f'<p>{hw_text}</p>')
                        html_parts.append('</div>')
                    
                    html_parts.append('</div>')  # End right column
                    html_parts.append('</div>')  # End subject-content
        
        return ''.join(html_parts)


class ExportTemplatePDFView(View):
    
    def get(self, request, date=None):
        from django.template.loader import render_to_string
        from .pdf_service import html_to_pdf_bytes
        
        # Parse the date
        if date:
            try:
                selected_date = datetime.strptime(date, '%d-%m-%y').date()
            except ValueError:
                messages.error(request, "Invalid date format")
                return redirect("history")
        else:
            selected_date = date_module.today()
        
        # Get daily data for the selected date
        daily_data = self.get_daily_data(selected_date, request)
        
        # Build HTML content using the same template as PDF export
        html_content = self.build_html_content(daily_data, selected_date)
        
        # Render the template
        doc_html = render_to_string('print/tiptap_pdf.html', {'doc_html': html_content})
        
        # Generate PDF
        pdf_bytes = html_to_pdf_bytes(doc_html)
        
        # Create PDF response
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="school_organizer_template_{selected_date.strftime("%d_%m_%Y")}.pdf"'
        
        return response
    
    def get_daily_data(self, selected_date, request):
        """Helper method to get daily data for template PDF export"""
        # Get all subjects scheduled for this day (active schedules only)
        scheduled_subjects = WeeklySchedule.objects.filter(day_of_week=selected_date.weekday() + 1, is_active=True).select_related("subject").order_by("position")
        
        daily_data = []
        
        for schedule in scheduled_subjects:
            # Check if user has access to this subject
            if schedule.subject and schedule.subject.created_by == request.user:
                # Get daily entry for this subject and date
                daily_entry = DailyEntry.objects.filter(
                    subject=schedule.subject,
                    date=selected_date,
                    created_by=request.user
                ).first()
                
                has_entry = daily_entry is not None
                
                # Get book information
                book_name = ""
                pages = ""
                if daily_entry and daily_entry.book:
                    book_name = daily_entry.book.title
                    pages = daily_entry.pages or ""
                
                # Get extras
                extras = []
                if daily_entry:
                    for extra in daily_entry.extras.all():
                        extra_data = {
                            'book_name': extra.book.title if extra.book else "",
                            'pages': extra.pages or ""
                        }
                        extras.append(extra_data)
                
                # Get homework
                homework = []
                if daily_entry:
                    for hw in daily_entry.homework_entries.all():
                        hw_data = {
                            'book_name': hw.book.title if hw.book else "",
                            'pages': hw.pages or ""
                        }
                        homework.append(hw_data)
                
                # Get notes and important notes
                notes = daily_entry.notes if daily_entry else ""
                important_notes = daily_entry.important_notes if daily_entry else ""
                
                daily_data.append({
                    'subject_name': schedule.subject.name,
                    'has_entry': has_entry,
                    'book_name': book_name,
                    'pages': pages,
                    'extras': extras,
                    'homework': homework,
                    'notes': notes,
                    'important_notes': important_notes,
                    'created_by': schedule.created_by
                })
        
        return daily_data
    
    def build_html_content(self, daily_data, selected_date):
        """Build HTML content from daily data for template PDF export (same as PDF)"""
        html_parts = []
        
        # Title
        html_parts.append(f'<h1 style="text-align: center; font-size: 18px; margin-bottom: 10px;">{selected_date.strftime("%d %B %Y")}</h1>')
        
        # Check if there's any data
        has_data = any(entry['has_entry'] for entry in daily_data)
        
        if not has_data:
            html_parts.append('<p>No data saved for this day.</p>')
        else:
            # Add each subject's data in template format
            for entry in daily_data:
                if entry['has_entry']:
                    # Subject title
                    html_parts.append(f'<h2 style="font-size: 16px; margin: 15px 0 8px 0;">{entry["subject_name"]}</h2>')
                    
                    # Start two-column layout
                    html_parts.append('<div class="subject-content">')
                    
                    # Left column: Resources and Notes
                    html_parts.append('<div class="left-column">')
        
        # Resources section
                    if entry['book_name'] or entry['extras']:
                        html_parts.append('<div class="section">')
                        html_parts.append('<div class="section-title">Ресурси:</div>')
                        
                        # Main book
                        if entry['book_name']:
                            resource_text = f"→ {entry['book_name']}"
                            if entry['pages']:
                                resource_text += f" стр. {entry['pages']}"
                            html_parts.append(f'<p>{resource_text}</p>')
                        
                        # Extra books
                        for extra in entry['extras']:
                            extra_text = f"→ {extra['book_name']}"
                            if extra['pages']:
                                extra_text += f" стр. {extra['pages']}"
                            html_parts.append(f'<p>{extra_text}</p>')
                        html_parts.append('</div>')
                    
                    # Notes
                    if entry['notes']:
                        html_parts.append('<div class="section">')
                        html_parts.append('<div class="section-title">Записки:</div>')
                        html_parts.append(entry['notes'])
                        html_parts.append('</div>')
                    
                    html_parts.append('</div>')  # End left column
                    
                    # Right column: Important Notes and Homework
                    html_parts.append('<div class="right-column">')
                    
                    # Important Notes
                    if entry.get('important_notes'):
                        html_parts.append('<div class="section">')
                        html_parts.append('<div class="section-title">Важно:</div>')
                        html_parts.append(entry['important_notes'])
                        html_parts.append('</div>')
                    
                    # Homework
                    if entry['homework']:
                        html_parts.append('<div class="section">')
                        html_parts.append('<div class="section-title">Домашно:</div>')
                        for hw in entry['homework']:
                            hw_text = f"→ {hw['book_name']}"
                            if hw['pages']:
                                hw_text += f" стр. {hw['pages']}"
                            html_parts.append(f'<p>{hw_text}</p>')
                        html_parts.append('</div>')
                    
                    html_parts.append('</div>')  # End right column
                    html_parts.append('</div>')  # End subject-content
        
        return ''.join(html_parts)


@method_decorator(csrf_exempt, name='dispatch')
class TodayAutoSaveAPIView(View):
    def post(self, request):
        """Auto-save today page data without page refresh"""
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        try:
            data = json.loads(request.body)
            
            # Get parameters
            subject_id = data.get('subject_id')
            date_str = data.get('date')
            username = data.get('username')
            user_id = data.get('user_id')
            
            # Parse date
            if date_str:
                today_date = datetime.strptime(date_str, '%d-%m-%y').date()
            else:
                from datetime import date as date_module
                today_date = date_module.today()
            
            # Determine target user
            if username and user_id:
                try:
                    target_user = User.objects.get(username__iexact=username, id=user_id)
                    can_edit = (target_user == request.user) or request.user.is_admin()
                    if not can_edit:
                        return JsonResponse({'error': 'Permission denied'}, status=403)
                except User.DoesNotExist:
                    target_user = request.user
            else:
                target_user = request.user
            
            if not subject_id:
                return JsonResponse({'error': 'Subject ID required'}, status=400)
            
            # Get form data
            book_id = data.get('book_id')
            pages = data.get('pages')
            notes = data.get('notes')
            important_notes = data.get('important_notes')
            
            # Process homework entries
            homework_entries = []
            for i in range(10):
                hw_book_id = data.get(f'homework_book_{i}')
                hw_pages = data.get(f'homework_pages_{i}')
                if hw_book_id:
                    homework_entries.append({
                        'book_id': hw_book_id,
                        'pages': hw_pages or ''
                    })
            
            # Process extra book entries
            extra_entries = []
            for i in range(10):
                extra_book_id = data.get(f'extra_book_{i}')
                extra_pages = data.get(f'extra_pages_{i}')
                if extra_book_id:
                    extra_entries.append({
                        'book_id': extra_book_id,
                        'pages': extra_pages or ''
                    })
            
            # Get subject
            try:
                subject = Subject.objects.get(id=subject_id, created_by=target_user)
            except Subject.DoesNotExist:
                return JsonResponse({'error': 'Subject not found'}, status=404)
            
            # Get book if book_id is provided
            book = None
            if book_id:
                try:
                    book = Book.objects.get(id=book_id, created_by=target_user)
                except Book.DoesNotExist:
                    pass  # book will remain None
            
            # Create or update daily entry
            daily_entry, created = DailyEntry.objects.get_or_create(
                subject=subject,
                date=today_date,
                created_by=target_user,
                defaults={
                    'notes': notes, 
                    'important_notes': important_notes,
                    'book': book,
                    'pages': pages
                }
            )
            
            if not created:
                daily_entry.notes = notes
                daily_entry.important_notes = important_notes
                daily_entry.book = book
                daily_entry.pages = pages
                daily_entry.save()
            
            # Handle extras
            if daily_entry:
                # Clear existing extras
                daily_entry.extras.all().delete()
                
                # Create new extras
                for extra_data in extra_entries:
                    try:
                        extra_book = Book.objects.get(id=extra_data['book_id'], created_by=target_user)
                        DailyExtra.objects.create(
                            daily_entry=daily_entry,
                            book=extra_book,
                            pages=extra_data['pages']
                        )
                    except Book.DoesNotExist:
                        pass  # Skip invalid book IDs
            
            # Handle homework
            if daily_entry:
                # Clear existing homework
                daily_entry.homework_entries.all().delete()
                
                # Create new homework entries
                for hw_data in homework_entries:
                    try:
                        hw_book = Book.objects.get(id=hw_data['book_id'], created_by=target_user)
                        HomeworkEntry.objects.create(
                            daily_entry=daily_entry,
                            book=hw_book,
                            pages=hw_data['pages']
                        )
                    except Book.DoesNotExist:
                        pass  # Skip invalid book IDs
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class UsersView(LoginRequiredMixin, View):
    def get(self, request):
        # Only admin users can access this page
        if not request.user.is_admin:
            return redirect('no_access')
        
        # Get all users with additional data
        users = User.objects.all().order_by('username')
        
        # Add unique days count for each user
        users_with_data = []
        for user in users:
            unique_days = user.dailyentry_set.values_list('date', flat=True).distinct().count()
            user.unique_days_count = unique_days
            users_with_data.append(user)
        
        context = {
            'users': users_with_data,
        }
        return render(request, 'users.html', context)


class SubjectsBooksAPIView(View):
    def get(self, request):
        """Get all subjects and their books for the current user"""
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        # Check if admin is managing another user's data
        target_user = request.user  # Default to current user
        if request.user.is_admin() and 'target_user_id' in request.session:
            try:
                target_user = User.objects.get(id=request.session['target_user_id'])
            except User.DoesNotExist:
                pass  # Fall back to current user
        
        # Show subjects for the target user
        subjects = Subject.objects.filter(created_by=target_user).order_by('name')
        
        data = []
        for subject in subjects:
            books = Book.objects.filter(subject=subject).order_by('title')
            data.append({
                'id': subject.id,
                'name': subject.name,
                'books': [{'id': book.id, 'title': book.title} for book in books]
            })
        
        return JsonResponse({'subjects': data})


class NoAccessView(View):
    def get(self, request):
        return render(request, 'no_access.html')

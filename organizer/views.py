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
from asgiref.sync import sync_to_async
import json
from django.contrib.auth.forms import UserCreationForm
from django import forms
from datetime import datetime, date as date_module, timedelta
import calendar

# ReportLab, pdf2image, and PIL imports removed - using Playwright for PDF/JPEG generation

from .models import Subject, Book, WeeklySchedule, DailyEntry, DailyExtra, HomeworkEntry, User, Test


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
        
        elif 'action' in request.POST and request.POST.get('action') == 'add_tests':
            # Add single test (for dynamic saving)
            test_date = request.POST.get('test_date')
            test_subject = request.POST.get('test_subject')
            
            if test_date and test_subject:
                try:
                    subject = Subject.objects.get(id=test_subject)
                    # Check if user can edit this subject
                    if request.user.can_edit(subject):
                        test_date_obj = datetime.strptime(test_date, '%Y-%m-%d').date()
                        test, created = Test.objects.get_or_create(
                            date=test_date_obj,
                            subject=subject,
                            defaults={'created_by': request.user}
                        )
                        if created:
                            return JsonResponse({'success': True, 'message': 'Test added successfully!'})
                        else:
                            return JsonResponse({'success': True, 'message': 'Test already exists for this date and subject.'})
                    else:
                        return JsonResponse({'success': False, 'error': 'You can only add tests for subjects you created!'})
                except Subject.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Subject not found!'})
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Invalid date format!'})
            else:
                return JsonResponse({'success': False, 'error': 'Please provide test date and subject!'})
        
        elif 'action' in request.POST and request.POST.get('action') == 'delete_test':
            # Delete single test
            test_date = request.POST.get('test_date')
            test_subject = request.POST.get('test_subject')
            
            if test_date and test_subject:
                try:
                    subject = Subject.objects.get(id=test_subject)
                    # Check if user can edit this subject
                    if request.user.can_edit(subject):
                        test_date_obj = datetime.strptime(test_date, '%Y-%m-%d').date()
                        test = Test.objects.get(
                            date=test_date_obj,
                            subject=subject,
                            created_by=request.user
                        )
                        test.delete()
                        return JsonResponse({'success': True, 'message': 'Test deleted successfully!'})
                    else:
                        return JsonResponse({'success': False, 'error': 'You can only delete tests for subjects you created!'})
                except Test.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Test not found!'})
                except Subject.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Subject not found!'})
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Invalid date format!'})
            else:
                return JsonResponse({'success': False, 'error': 'Please provide test date and subject!'})
        
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
        
        # Get days with tests for highlighting
        days_with_tests = self.get_days_with_tests(year, month, target_user)
        
        # Get daily data if a date is selected
        daily_data = None
        tests_data = None
        if selected_date:
            daily_data = self.get_daily_data(selected_date, target_user)
            tests_data = self.get_tests_data(selected_date, target_user)
        
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
            'days_with_tests': days_with_tests,
            'selected_date': selected_date,
            'daily_data': daily_data,
            'tests_data': tests_data,
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
    
    def get_days_with_tests(self, year, month, target_user=None):
        """Get list of days that have tests for the given month."""
        first_day = date_module(year, month, 1)
        last_day = date_module(year, month, calendar.monthrange(year, month)[1])
        
        # Filter tests based on user role and target_user
        if target_user:
            # Anonymous user viewing specific user's data OR logged-in user viewing their own data
            tests = Test.objects.filter(
                date__gte=first_day,
                date__lte=last_day,
                created_by=target_user
            )
        elif not self.request.user.is_authenticated:
            # Anonymous users see no tests unless viewing specific user's data
            tests = Test.objects.none()
        elif self.request.user.is_admin():
            # Admin viewing their own history should only see their own tests
            tests = Test.objects.filter(
                date__gte=first_day,
                date__lte=last_day,
                created_by=self.request.user
            )
        else:  # Teacher - only their own tests
            tests = Test.objects.filter(
                date__gte=first_day,
                date__lte=last_day,
                created_by=self.request.user
            )
        
        return [test.date.day for test in tests]
    
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
                
                # Only add this subject if it has meaningful content
                has_content = (
                    daily_entry.book or  # Has a book
                    daily_entry.pages or  # Has pages
                    daily_entry.notes or  # Has notes
                    daily_entry.important_notes or  # Has important notes
                    extra_books or  # Has extra books
                    homework_books  # Has homework
                )
                
                if has_content:
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
                
                # Only add this subject if it has meaningful content
                has_content = (
                    daily_entry.book or  # Has a book
                    daily_entry.pages or  # Has pages
                    daily_entry.notes or  # Has notes
                    daily_entry.important_notes or  # Has important notes
                    extra_books or  # Has extra books
                    homework_books  # Has homework
                )
                
                if has_content:
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
    
    def get_tests_data(self, selected_date, target_user=None):
        """Get all tests for the selected date."""
        # Get the target user for filtering
        if target_user:
            user_to_filter = target_user
        elif not self.request.user.is_authenticated:
            # Anonymous users see no tests unless viewing specific user's data
            return []
        elif self.request.user.is_admin():
            user_to_filter = self.request.user
        else:  # Teacher - only their own tests
            user_to_filter = self.request.user
        
        # Get tests for this date
        tests = Test.objects.filter(
            date=selected_date,
            created_by=user_to_filter
        ).select_related('subject').order_by('subject__name')
        
        return [{'subject_name': test.subject.name} for test in tests]


# ExportPDFView class removed - using ExportTemplatePDFView instead


class ExportJPEGView(View):
    def get(self, request, date=None):
        from django.template.loader import render_to_string
        from .pdf_service import get_browser
        
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
        
        try:
            # Use Playwright to generate JPEG (screenshot)
            browser = get_browser()
            page = browser.new_page()
            
            try:
                # Set content directly - no external resources needed for our use case
                page.set_content(html, wait_until="domcontentloaded")
                
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
        """Helper method to get daily data for JPEG export"""
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
                
                # Only add this subject if it has meaningful content
                has_content = (
                    main_entry.book or  # Has a book
                    main_entry.pages or  # Has pages
                    main_entry.notes or  # Has notes
                    main_entry.important_notes or  # Has important notes
                    extras or  # Has extra books
                    homework_books  # Has homework
                )
                
                if has_content:
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
                # No entry for this subject - skip it (don't add empty subjects)
                continue
        
        return daily_data

    # Old ReportLab methods removed - using Playwright for PDF generation
    
class ExportTemplatePDFView(View):
    def get(self, request, date=None):
        from django.template.loader import render_to_string
        
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
        html = render_to_string('print/tiptap_pdf.html', {'doc_html': html_content})
        base_url = request.build_absolute_uri("/")
        
        # Generate PDF using Playwright
        from .pdf_service import html_to_pdf_bytes
        pdf_bytes = html_to_pdf_bytes(html, base_url=base_url)
        
        # Create PDF response
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="school_organizer_{selected_date.strftime("%d_%m_%Y")}.pdf"'
        
        return response
    
    def get_daily_data(self, selected_date, request):
        """Helper method to get daily data for PDF export"""
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
                
                # Only add this subject if it has meaningful content
                has_content = (
                    book_name or  # Has a book
                    pages or  # Has pages
                    notes or  # Has notes
                    important_notes or  # Has important notes
                    extras or  # Has extra books
                    homework  # Has homework
                )
                
                if has_content:
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
        """Build HTML content from daily data for PDF export (ALL content: Ресурси, Записки, Важно, Домашно)"""
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
                    
                    # Notes - INCLUDED for PDF export (show ALL content)
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

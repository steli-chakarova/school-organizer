from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('no-access/', views.NoAccessView.as_view(), name='no_access'),
    
    # Main app URLs
    path('home/<str:username>/<int:user_id>/', views.HomeUserView.as_view(), name='home_user'),
    path('', views.HomeView.as_view(), name='home'),
    path('users/', views.UsersView.as_view(), name='users'),
    path('schedule/manage/', views.ScheduleManagementView.as_view(), name='schedule_manage'),
    path('today/', views.TodayView.as_view(), name='today'),
    path('today/<str:username>/<int:user_id>/<str:date>/', views.TodayView.as_view(), name='today_user_date'),
    path('today/<str:username>/<int:user_id>/', views.TodayView.as_view(), name='today_user'),
    path('today/<str:date>/', views.TodayView.as_view(), name='today_date'),
    path('history/<str:username>/<int:user_id>/', views.HistoryView.as_view(), name='history_user'),
    path('history/<str:username>/<int:user_id>/<str:date>/', views.HistoryView.as_view(), name='history_user_date'),
    path('export/pdf/', views.ExportPDFView.as_view(), name='export_pdf'),
    path('export/pdf/<str:date>/', views.ExportPDFView.as_view(), name='export_pdf_date'),
    path('export/jpeg/', views.ExportJPEGView.as_view(), name='export_jpeg'),
    path('export/jpeg/<str:date>/', views.ExportJPEGView.as_view(), name='export_jpeg_date'),
    path('export/template/', views.ExportTemplatePDFView.as_view(), name='export_template'),
    path('export/template/<str:date>/', views.ExportTemplatePDFView.as_view(), name='export_template_date'),
    
    # API endpoints
    path('api/subjects-books/', views.SubjectsBooksAPIView.as_view(), name='subjects_books_api'),
    path('api/today-autosave/', views.TodayAutoSaveAPIView.as_view(), name='today_autosave_api'),
]

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView


class TokenObtainRateThrottle(AnonRateThrottle):
    rate = '10/minute'


TokenObtainPairView.throttle_classes = [TokenObtainRateThrottle]

from .views import (
    AchievementViewSet,
    AdminUserViewSet,
    AllActiveLoansViewSet,
    AllBooksViewSet,
    AllUsersViewSet,
    BookDetailViewSet,
    # User
    CatalogViewSet,
    ChallengeViewSet,
    CsvExportView,
    CsvImportView,
    DistrictViewSet,
    GraduateViewSet,
    InstitutionViewSet,
    LeaderboardView,
    # Auth
    LoginView,
    LogoutView,
    MeView,
    MyBooksViewSet,
    MyClassView,
    MyProfileViewSet,
    NewsViewSet,
    QrProcessView,
    # Reports
    ReportViewSet,
    SchoolBookViewSet,
    # School
    SchoolDashboardView,
    SchoolHistoryViewSet,
    SchoolIssueViewSet,
    SchoolStatsView,
    SchoolStudentViewSet,
    SchoolTeacherViewSet,
    # Admin
    SchoolViewSet,
    SuperUserStatsView,
    SystemLogsView,
    TextbookLoanViewSet,
    WaitlistViewSet,
)

router = DefaultRouter()

# Admin (superuser)
router.register(r'admin/schools', SchoolViewSet, basename='admin-school')
router.register(r'admin/districts', DistrictViewSet, basename='admin-district')
router.register(r'admin/institutions', InstitutionViewSet, basename='admin-institution')
router.register(r'admin/users', AllUsersViewSet, basename='admin-users')
router.register(r'admin/admins', AdminUserViewSet, basename='admin-admins')
router.register(r'admin/books', AllBooksViewSet, basename='admin-books')
router.register(r'admin/loans', AllActiveLoansViewSet, basename='admin-loans')
router.register(r'admin/logs', SystemLogsView, basename='admin-logs')
router.register(r'admin/stats', SuperUserStatsView, basename='admin-stats')
router.register(r'admin/reports', ReportViewSet, basename='admin-reports')

# School (school_admin)
router.register(r'school/dashboard', SchoolDashboardView, basename='school-dashboard')
router.register(r'school/students', SchoolStudentViewSet, basename='school-students')
router.register(r'school/teachers', SchoolTeacherViewSet, basename='school-teachers')
router.register(r'school/books', SchoolBookViewSet, basename='school-books')
router.register(r'school/issues', SchoolIssueViewSet, basename='school-issues')
router.register(r'school/history', SchoolHistoryViewSet, basename='school-history')
router.register(r'school/stats', SchoolStatsView, basename='school-stats')
router.register(r'school/qr', QrProcessView, basename='school-qr')
router.register(r'school/textbooks', TextbookLoanViewSet, basename='school-textbooks')
router.register(r'school/export', CsvExportView, basename='school-export')
router.register(r'school/import', CsvImportView, basename='school-import')
router.register(r'school/graduates', GraduateViewSet, basename='school-graduates')
router.register(r'school/reports', ReportViewSet, basename='school-reports')

# User (student/teacher)
router.register(r'library/catalog', CatalogViewSet, basename='user-catalog')
router.register(r'library/books', BookDetailViewSet, basename='user-book-detail')
router.register(r'library/my-books', MyBooksViewSet, basename='user-mybooks')
router.register(r'library/profile', MyProfileViewSet, basename='user-profile')
router.register(r'library/achievements', AchievementViewSet, basename='user-achievements')
router.register(r'library/challenges', ChallengeViewSet, basename='user-challenges')
router.register(r'library/leaderboard', LeaderboardView, basename='user-leaderboard')
router.register(r'library/waitlist', WaitlistViewSet, basename='user-waitlist')
router.register(r'library/news', NewsViewSet, basename='user-news')
router.register(r'library/my-class', MyClassView, basename='user-myclass')

urlpatterns = [
    # Auth
    path('auth/login/', LoginView, name='auth-login'),
    path('auth/logout/', LogoutView, name='auth-logout'),
    path('auth/me/', MeView, name='auth-me'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token-verify'),
    # Versioned API
    path('v1/', include(router.urls)),
]

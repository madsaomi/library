from .accounts import (
    ChangePasswordSerializer,
    CustomUserCreateSerializer,
    CustomUserDetailSerializer,
    CustomUserSerializer,
)
from .books import (
    AchievementSerializer,
    BookIssueSerializer,
    BookListSerializer,
    BookRequestSerializer,
    BookSerializer,
    BookWaitlistSerializer,
    CategorySerializer,
    ChallengeSerializer,
    ReaderOfMonthSerializer,
    TextbookLoanSerializer,
    UserAchievementSerializer,
    UserChallengeSerializer,
)
from .news import NewsSerializer
from .schools import DistrictSerializer, InstitutionSerializer, SchoolSerializer, SubjectSerializer
from .stats import ActionLogSerializer

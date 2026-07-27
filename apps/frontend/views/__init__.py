from .admin_views import (
    admin_add,
    admin_edit,
    admin_global_search,
    admin_health,
    all_active_loans_list,
    all_books_list,
    all_users_list,
    check_username,
    create_stats_news,
    district_add,
    district_delete,
    district_edit,
    districts_list,
    muassasa_add,
    muassasa_delete,
    muassasa_edit,
    muassasalar_list,
    school_add,
    school_delete,
    school_detail,
    school_edit,
    schools_list,
    statistics_json,
    system_logs,
    user_detail,
)
from .admin_views import (
    change_password as admin_change_password,
)
from .admin_views import (
    dashboard as admin_dashboard,
)
from .admin_views import (
    news_add as admin_news_add,
)
from .admin_views import (
    news_delete as admin_news_delete,
)
from .admin_views import (
    news_edit as admin_news_edit,
)
from .admin_views import (
    news_list as admin_news_list,
)
from .admin_views import (
    profile as admin_profile,
)
from .admin_views import (
    statistics as admin_statistics,
)
from .school_views import (
    book_add,
    book_delete,
    book_edit,
    export_books_csv,
    export_issues_csv,
    export_students_csv,
    graduates_list,
    history_list,
    import_books_csv,
    import_students_csv,
    issued_books_list,
    post_top_student_news,
    process_qr,
    process_qr_unified,
    process_receive_qr,
    qr_unified,
    student_add,
    student_delete,
    student_detail,
    student_edit,
    students_list,
    teacher_add,
    teacher_delete,
    teacher_edit,
    teachers_list,
    textbook_collect,
    textbook_distribute,
    textbook_loans,
)
from .school_views import (
    books_list as school_books_list,
)
from .school_views import (
    change_password as school_change_password,
)
from .school_views import (
    dashboard as school_dashboard,
)
from .school_views import (
    news_add as school_news_add,
)
from .school_views import (
    news_delete as school_news_delete,
)
from .school_views import (
    news_edit as school_news_edit,
)
from .school_views import (
    news_list as school_news_list,
)
from .school_views import (
    profile as school_profile,
)
from .school_views import (
    statistics as school_statistics,
)
from .user_views import (
    achievements,
    book_detail,
    challenges,
    check_request_status,
    check_return_status,
    get_rotating_token,
    issue_qr,
    join_waitlist,
    leaderboard,
    leave_waitlist,
    library,
    my_books,
    my_class,
    profile_edit,
    request_qr,
    reserve_book,
)
from .user_views import (
    change_password as user_change_password,
)
from .user_views import (
    news_list as user_news_list,
)
from .user_views import (
    profile as user_profile,
)

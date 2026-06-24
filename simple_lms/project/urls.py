"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from lms import views
from lms.views import user_stat_view
from lms.apiv1 import apiv1
from lms.apiv2 import apiv2

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.dashboard),
    path('dashboard/', views.dashboard),

    path('login/', views.login_view),
    path('register/', views.register_view),
    path('logout/', views.logout_view),

    path('users/', views.user_list),
    path('users/json/', views.user_json),
    path('users/filter/', views.user_filter),
    path('users/<int:id>/', views.user_detail),

    path('users/stat/', user_stat_view),        # ✅ HTML
    path('users/stat/json/', views.userstat),   # ✅ JSON (opsional)

    path('courses/create/', views.create_course),
    path('courses/list/', views.course_list_view),
    path('courses/all/', views.allcourse),
    path('courses/user/<int:user_id>/', views.userCourses),
    path('courses/stat/', views.coursestat),
    path('courses/member-stat/', views.courseMemberStat),
    path('courses/relasi/', views.course_relasi),
    path('courses/<int:id>/delete/', views.delete_course_view),

    path('import/', views.upload_csv),
    path('import/template/', views.download_csv_template),

    path('comments/', views.comment_list),
    path('content/', views.content_list),
    path('content/add/', views.add_content),
    path('content/<int:id>/', views.content_list),

    path('dashboard/stat/', views.course_dashboard_stat),

    path('courses-api/', views.courses_api_view),
    path('quick-actions/', views.quick_actions_view),

    path('api/v1/', apiv1.urls),
    path('api/v2/', apiv2.urls),
]

if settings.DEBUG:
    # Profiling Django Silk hanya aktif saat development, supaya tidak
    # menambah overhead/risiko di production (Railway).
    urlpatterns += [path('silk/', include('silk.urls', namespace='silk'))]

# Layani media files (upload gambar/PDF) langsung dari Django.
# Untuk proyek skala kecil seperti ini cukup aman dipakai juga di production,
# asalkan MEDIA_ROOT di-mount ke Railway Volume supaya filenya persisten.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
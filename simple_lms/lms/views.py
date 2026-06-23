from django.db.models import Max, Min, Avg, Count
from .models import Course, CourseMember, Comment, CourseContent, models
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.core import serializers
import csv
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
import re
from django.shortcuts import render
from .models import CourseContent




# =========================
# LIST USER (HTML)
# =========================
def user_list(request):
    users = User.objects.all()
    return render(request, 'lms/user_list.html', {'users': users})


# =========================
# LIST USER (JSON)
# =========================
def user_json(request):
    users = list(User.objects.values('id', 'username', 'email'))
    return JsonResponse(users, safe=False)


# =========================
# UPLOAD CSV (COURSE)
# =========================
def upload_csv(request):
    if request.method == 'POST':
        try:
            file = request.FILES['file']
            data = file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(data)

            teacher = User.objects.first()
            course_list = []

            for row in reader:
                if not Course.objects.filter(name=row['name']).exists():
                    course_list.append(
                        Course(
                            name=row['name'],
                            description=row['description'],
                            price=int(row['price']),
                            teacher=teacher
                        )
                    )

            # 🔥 INSERT SEKALIGUS
            Course.objects.bulk_create(course_list)

            return render(request, 'lms/upload.html', {
                'message': f'✅ {len(course_list)} data berhasil diupload!'
            })

        except Exception as e:
            return render(request, 'lms/upload.html', {
                'error': f'❌ Error: {str(e)}'
            })

    return render(request, 'lms/upload.html')

# =========================
# HALAMAN IMPORT CSV (FIX ERROR URL)
# =========================
def import_csv_page(request):
    return render(request, 'lms/upload.html')


# =========================
# DETAIL USER (GET)
# =========================
def user_detail(request, id):
    user = User.objects.get(pk=id)
    return render(request, 'lms/user_detail.html', {'user': user})


# =========================
# FILTER USER
# =========================
def user_filter(request):
    users = User.objects.filter(username="usertesting")
    return JsonResponse(list(users.values()), safe=False)


# =========================
# UPDATE USER
# =========================
def update_user(request):
    user = User.objects.get(username="usertesting")
    user.email = "updated@email.com"
    user.save()

    return JsonResponse({"status": "user updated"})


# =========================
# DELETE USER
# =========================
def delete_user(request):
    user = User.objects.get(username="usertesting")
    user.delete()

    return JsonResponse({"status": "user deleted"})


# =========================
# DELETE ALL COURSE
# =========================
def delete_all_course(request):
    Course.objects.all().delete()
    return JsonResponse({"status": "all course deleted"})


# =========================
# DELETE USER KECUALI ADMIN
# =========================
def delete_except_admin(request):
    User.objects.exclude(pk=1).delete()
    return JsonResponse({"status": "deleted except admin"})


# =========================
# SELECT COURSE + TEACHER
# =========================
def allcourse(request):
    allcourse = Course.objects.select_related('teacher').all()

    result = []

    for course in allcourse:
        result.append({
            'id': course.id,
            'name': course.name,
            'description': course.description,
            'price': course.price,
            'teacher': {
                'id': course.teacher.id,
                'username': course.teacher.username,
                'email': course.teacher.email
            }
        })

    return JsonResponse(result, safe=False)


# =========================
# USER + COURSE (RELASI MEMBER)
# =========================

def userCourses(request, user_id):
    # ✅ aman (hindari error 500)
    user = get_object_or_404(User, pk=user_id)

    # ✅ optimasi query (JOIN + hindari N+1)
    courses = Course.objects.select_related('teacher') \
        .filter(coursemember__user=user)

    course_data = []

    for course in courses:
        course_data.append({
            'id': course.id,
            'name': course.name,
            'description': course.description,
            'price': course.price,
            'teacher': course.teacher.username  # optional tapi bagus
        })

    result = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'fullname': f"{user.first_name} {user.last_name}",
        'courses': course_data
    }

    return JsonResponse(result)


# =========================
# AGGREGATE (STATISTIK COURSE)
# =========================
def coursestat(request):
    courses = Course.objects.all()

    stats = courses.aggregate(
        max_price=Max('price'),
        min_price=Min('price'),
        avg_price=Avg('price')
    )

    def format_course(qs):
        data = []
        for c in qs:
            data.append({
                "model": "lms.course",
                "pk": c.id,
                "fields": {
                    "name": c.name,
                    "description": c.description,
                    "price": c.price,
                    "image": c.image.url if c.image else "",  # ✅ FIX ERROR
                    "teacher": c.teacher.id if c.teacher else None,
                    "created_at": str(c.created_at) if hasattr(c, 'created_at') else "",
                    "updated_at": str(c.updated_at) if hasattr(c, 'updated_at') else ""
                }
            })
        return data

    # CHEAPEST & EXPENSIVE
    cheapest_qs = Course.objects.filter(price=stats['min_price'])
    expensive_qs = Course.objects.filter(price=stats['max_price'])

    # POPULAR (BERDASARKAN MEMBER)
    popular_qs = Course.objects.annotate(
        member_count=Count('coursemember')
    ).order_by('-member_count')[:3]

    result = {
        "course_count": courses.count(),
        "courses": {
            "max_price": stats['max_price'],
            "min_price": stats['min_price'],
            "avg_price": int(stats['avg_price']) if stats['avg_price'] else 0
        },
        "cheapest": format_course(cheapest_qs),
        "expensive": format_course(expensive_qs),
        "popular": format_course(popular_qs)
    }

    return JsonResponse(result, safe=False)
# =========================
# FILTER + AGGREGATE + COUNT
# =========================
def courseMemberStat(request):
    courses = Course.objects.filter(description__icontains='python') \
        .annotate(member_num=Count('coursemember'))

    course_data = []

    for course in courses:
        record = {
            'id': course.id,
            'name': course.name,
            'price': course.price,
            'member_count': course.member_num
        }
        course_data.append(record)

    result = {
        'data_count': len(course_data),
        'data': course_data
    }

    return JsonResponse(result)


# =========================
# CREATE COURSE (FIX DUPLIKAT + SEARCH)
# =========================
def create_course(request):
    users = User.objects.all()

    # 🔍 ambil keyword search
    search_query = request.GET.get('search')

    # 🔥 filter course
    if search_query:
        courses = Course.objects.filter(name__icontains=search_query)
    else:
        courses = Course.objects.all()

    if request.method == 'POST':
        course = Course.objects.create(
            name=request.POST['name'],
            description=request.POST['description'],
            price=int(request.POST['price']),
            teacher=User.objects.get(pk=request.POST['teacher'])
        )

        youtube_url = clean_youtube_url(request.POST.get('youtube_url'))
        materi_pdf = request.FILES.get('materi_pdf')

        if youtube_url or materi_pdf:
            CourseContent.objects.create(
                name=f"Materi Pengantar - {course.name}",
                course=course,
                video_url=youtube_url,
                file_attachment=materi_pdf
            )

        return redirect('/courses/create/')

    return render(request, 'lms/create_course.html', {
        'users': users,
        'courses': courses,
        'search_query': search_query  # 🔥 kirim ke HTML
    })

#=================
#DASHBOARD
#=================

def dashboard(request):
    total_users = User.objects.filter(is_superuser=False).count()
    total_courses = Course.objects.count()
    total_members = User.objects.filter(is_superuser=False).count()

    courses = Course.objects.all()

    # ✅ tambahan statistik (tanpa merusak struktur lama)
    avg_price = Course.objects.aggregate(avg=Avg('price'))['avg']

    context = {
        'user_count': total_users,
        'course_count': total_courses,
        'member_count': total_members,
        'courses': courses,
        'avg_price': int(avg_price) if avg_price else 0  # aman dari None
    }

    return render(request, 'lms/dashboard.html', context)

# =========================
# QUERY RELASI (COURSE + TEACHER + MEMBER)
# =========================
def course_relasi(request):
    courses = Course.objects.select_related('teacher') \
                            .prefetch_related('coursemember_set')

    result = []

    for course in courses:
        result.append({
            'course_name': course.name,
            'teacher': course.teacher.username,
            'total_member': course.coursemember_set.count()
        })

    return JsonResponse(result, safe=False)

# =========================
# USER STATISTIK
# =========================
def userstat(request):
    users = User.objects.all()

    result = {
        'total_user': users.filter(is_superuser=False).count(),
        'total_admin': users.filter(is_superuser=True).count(),
        'total_user_biasa': users.filter(is_superuser=False).count()
    }

    return JsonResponse(result)

# =========================
# KOMENTAR & DISKUSI
# =========================
def comment_list(request):

    comments = Comment.objects.select_related(
        'member_id__user_id',
        'content_id'
    ).all().order_by('-created_at')

    return render(request, 'lms/comment_list.html', {
        'comments': comments
    })

# =========================
# FUNCTION CLEAN YOUTUBE URL
# =========================
def clean_youtube_url(url):
    if not url:
        return None

    import re

    pattern = r"(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)

    if match:
        video_id = match.group(1)

        return f"https://www.youtube.com/embed/{video_id}?rel=0"

    return None


# =========================
# LIST CONTENT
# =========================
def content_list(request):

    # =========================
    # SIMPAN KOMENTAR
    # =========================
    if request.method == 'POST':

        content_id = request.POST.get('content_id')
        comment_text = request.POST.get('comment')

        content = CourseContent.objects.get(id=content_id)

        # 🔥 sementara ambil member pertama
        member = CourseMember.objects.first()

        if member and comment_text:
            Comment.objects.create(
                content_id=content,
                member_id=member,
                comment=comment_text
            )

        return redirect('/content/')

    # =========================
    # AMBIL CONTENT + KOMENTAR
    # =========================
    contents = CourseContent.objects.prefetch_related(
        'comments__member_id__user_id'
    ).all()

    return render(request, 'lms/content_list.html', {
        'contents': contents
    })

# =========================
# ADD CONTENT
# =========================
def add_content(request):
    if request.method == 'POST':
        video_url = request.POST.get('video_url')
        video_url = clean_youtube_url(video_url)  # 🔥 FIX UTAMA

        CourseContent.objects.create(
            name=request.POST.get('name'),
            description=request.POST.get('description', ''),
            video_url=video_url,
            file_attachment=request.FILES.get('file_attachment'),
            course_id_id=request.POST.get('course')
        )

        return redirect('/content/')

    courses = Course.objects.all()

    return render(request, 'lms/add_content.html', {
        'courses': courses
    })
# =========================
# USER STATISTIK (HTML VIEW)
# =========================
def user_stat_view(request):
    total_users = User.objects.filter(is_superuser=False).count()
    total_admin = User.objects.filter(is_superuser=True).count()
    total_courses = Course.objects.count()
    total_comments = Comment.objects.count()

    context = {
        'total_users': total_users,   # ✅ hanya user biasa
        'total_admin': total_admin,
        'total_courses': total_courses,
        'total_comments': total_comments
    }

    return render(request, 'lms/user_stat.html', context)


from django.db.models import Max, Min, Avg, Count, Q

def course_dashboard_stat(request):
    # =========================
    # BASIC
    # =========================
    total_course = Course.objects.count()

    # 🔥 FIX TOTAL MEMBER (TANPA ADMIN + TANPA DUPLIKAT)
    total_member = CourseMember.objects.exclude(
        user_id__is_superuser=True
    ).values('user_id').distinct().count()

    # =========================
    # PRICE STATS
    # =========================
    price_stats = Course.objects.aggregate(
        avg_price=Avg('price'),
        max_price=Max('price'),
        min_price=Min('price')
    )

    # =========================
    # POPULAR COURSE (FIX DOUBLE + TANPA ADMIN)
    # =========================
    popular_courses = Course.objects.annotate(
        member_count=Count(
            'coursemember',
            filter=Q(coursemember__user_id__is_superuser=False),
            distinct=True   # 🔥 WAJIB supaya tidak double
        )
    ).order_by('-member_count')[:5]

    # =========================
    # TERMURAH & TERMAHAL
    # =========================
    cheapest_courses = Course.objects.filter(price=price_stats['min_price'])
    expensive_courses = Course.objects.filter(price=price_stats['max_price'])

    # =========================
    # JUMLAH KONTEN
    # =========================
    content_stats = Course.objects.annotate(
        content_count=Count('contents', distinct=True)
    )

    # =========================
    # JUMLAH KOMENTAR
    # =========================
    comment_stats = Course.objects.annotate(
    comment_count=Count('contents__comments', distinct=True)

)
    # =========================
    # CONTEXT
    # =========================
    context = {
        'total_course': total_course,
        'total_member': total_member,  
        'avg_price': int(price_stats['avg_price']) if price_stats['avg_price'] else 0,
        'max_price': price_stats['max_price'] or 0,
        'min_price': price_stats['min_price'] or 0,

        'popular_courses': popular_courses,
        'cheapest_courses': cheapest_courses,
        'expensive_courses': expensive_courses,
        'content_stats': content_stats,
        'comment_stats': comment_stats,
    }

    return render(request, 'lms/course_dashboard.html', context)


# =========================
# LOGIN
# =========================
def login_view(request):

    if request.user.is_authenticated:
        return redirect('/dashboard/')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('/dashboard/')

        return render(request, 'lms/login.html', {
            'error': 'Username atau password salah'
        })

    return render(request, 'lms/login.html')


# =========================
# REGISTER
# =========================
def register_view(request):

    if request.user.is_authenticated:
        return redirect('/dashboard/')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        if password != password2:
            return render(request, 'lms/register.html', {
                'error': 'Konfirmasi password tidak cocok'
            })

        if User.objects.filter(username=username).exists():
            return render(request, 'lms/register.html', {
                'error': 'Username sudah dipakai'
            })

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        login(request, user)

        return redirect('/dashboard/')

    return render(request, 'lms/register.html')


# =========================
# LOGOUT
# =========================
def logout_view(request):

    logout(request)

    return redirect('/login/')


# =========================
# COURSES API v2 (Search, Sort, Pagination)
# =========================
def courses_api_view(request):
    return render(request, 'lms/courses_api.html')
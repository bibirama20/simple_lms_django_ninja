import django
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Max, Min, Avg, Count, Q
from django.db.models.deletion import RestrictedError
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from .models import Course, CourseMember, Comment, CommentReply, CourseContent, ContentProgress, Note, Certificate, COURSE_CATEGORIES, models
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.core import serializers
import csv
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
import re
import secrets
import uuid
from io import BytesIO
from urllib.parse import urlencode
import requests
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas as pdf_canvas
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.shortcuts import render
from .models import CourseContent




# =========================
# LIST USER (HTML) + TAMBAH USER
# =========================
@login_required
def user_list(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        is_admin = request.POST.get('is_admin') == 'on'

        if not username or not password:
            messages.error(request, '❌ Username dan password wajib diisi.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, f'❌ Username "{username}" sudah dipakai.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            if is_admin:
                user.is_staff = True
                user.is_superuser = True
                user.save()
            messages.success(request, f'✅ User "{username}" berhasil dibuat.')

        return redirect('/users/')

    search_query = request.GET.get('search', '').strip()
    users = User.objects.all().order_by('-date_joined')

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) | Q(email__icontains=search_query)
        )

    return render(request, 'lms/user_list.html', {
        'active_page': 'users',
        'users': users,
        'search_query': search_query,
    })


# =========================
# LIST USER (JSON)
# =========================
def user_json(request):
    users = list(User.objects.values('id', 'username', 'email'))
    return JsonResponse(users, safe=False)


# =========================
# UPLOAD CSV (COURSE)
# =========================
@login_required
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
@login_required
def user_detail(request, id):
    user = User.objects.get(pk=id)
    return render(request, 'lms/user_detail.html', {'active_page': 'users', 'user': user})


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
@login_required
def create_course(request):
    users = User.objects.all()

    # 🔍 ambil keyword search
    search_query = request.GET.get('search')
    sort = request.GET.get('sort', 'terbaru')

    # 🔥 filter course + hitung jumlah member unik per course (untuk badge Best Seller)
    # Pakai 'coursemember__user_id' (bukan 'coursemember') supaya distinct
    # menghitung user unik, bukan baris CourseMember unik (user bisa saja
    # punya lebih dari satu baris keanggotaan pada course yang sama).
    courses = Course.objects.select_related('teacher').annotate(
        member_count=Count(
            'coursemember__user_id',
            filter=Q(coursemember__user_id__is_superuser=False),
            distinct=True
        )
    )

    if search_query:
        courses = courses.filter(name__icontains=search_query)

    courses = courses.order_by('created_at' if sort == 'lama' else '-created_at')

    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        youtube_url = clean_youtube_url(request.POST.get('youtube_url'))
        materi_pdf = request.FILES.get('materi_pdf')
        video_file = request.FILES.get('video_file')

        if course_id:
            course = get_object_or_404(Course, pk=course_id)
            course.name = request.POST['name']
            course.description = request.POST['description']
            course.price = int(request.POST['price'])
            course.teacher = User.objects.get(pk=request.POST['teacher'])
            course.category = request.POST.get('category', course.category)
            course.save()

            if youtube_url or materi_pdf or video_file:
                content = course.contents.first()
                if content:
                    if youtube_url:
                        content.video_url = youtube_url
                    if video_file:
                        content.video_file = video_file
                    if materi_pdf:
                        content.file_attachment = materi_pdf
                    content.save()
                else:
                    CourseContent.objects.create(
                        name=f"Materi Pengantar - {course.name}",
                        course=course,
                        video_url=youtube_url,
                        video_file=video_file,
                        file_attachment=materi_pdf
                    )

            messages.success(request, f'✅ Course "{course.name}" berhasil diperbarui.')
        else:
            course = Course.objects.create(
                name=request.POST['name'],
                description=request.POST['description'],
                price=int(request.POST['price']),
                teacher=User.objects.get(pk=request.POST['teacher']),
                category=request.POST.get('category', 'development')
            )

            if youtube_url or materi_pdf or video_file:
                CourseContent.objects.create(
                    name=f"Materi Pengantar - {course.name}",
                    course=course,
                    video_url=youtube_url,
                    video_file=video_file,
                    file_attachment=materi_pdf
                )

            messages.success(request, f'🚀 Course "{course.name}" berhasil diterbitkan.')

        return redirect('/courses/create/')

    # 🏆 best seller = course dengan member terbanyak (minimal 1 member riil)
    best_seller_id = None
    top = courses.order_by('-member_count').first()
    if top and top.member_count > 0:
        best_seller_id = top.id

    # 💰 format harga ala "Rp 450.000" (titik sebagai pemisah ribuan)
    for c in courses:
        c.price_fmt = f"{c.price:,}".replace(',', '.')

    edit_course = None
    edit_id = request.GET.get('edit')
    if edit_id:
        edit_course = Course.objects.filter(pk=edit_id).select_related('teacher').first()

    return render(request, 'lms/create_course.html', {
        'active_page': 'course_management',
        'users': users,
        'courses': courses,
        'search_query': search_query,  # 🔥 kirim ke HTML
        'sort': sort,
        'best_seller_id': best_seller_id,
        'edit_course': edit_course,
        'categories': COURSE_CATEGORIES,
    })


# =========================
# DELETE COURSE (PER-ITEM)
# =========================
@login_required
def delete_course_view(request, id):
    if request.method == 'POST':
        course = get_object_or_404(Course, pk=id)
        name = course.name
        try:
            course.delete()
            messages.success(request, f'🗑️ Course "{name}" berhasil dihapus.')
        except RestrictedError:
            messages.error(
                request,
                f'❌ Course "{name}" tidak bisa dihapus karena masih memiliki konten/member terdaftar.'
            )
    return redirect('/courses/create/')


# =========================
# DOWNLOAD TEMPLATE CSV
# =========================
@login_required
def download_csv_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="template_import_course.csv"'
    writer = csv.writer(response)
    writer.writerow(['name', 'description', 'price'])
    writer.writerow(['Belajar Django Ninja', 'Membangun REST API modern dengan Django Ninja', '150000'])
    return response

#=================
#DASHBOARD
#=================

def _dashboard_redirect_url(user):
    return '/dashboard/' if user.is_superuser else '/learn/'


def _price_fmt(price):
    return f"{price:,}".replace(',', '.')


@login_required
def dashboard(request):
    total_users = User.objects.filter(is_superuser=False).count()
    total_courses = Course.objects.count()
    total_members = CourseMember.objects.exclude(
        user_id__is_superuser=True
    ).values('user_id').distinct().count()

    popular_courses = Course.objects.annotate(
        member_count=Count(
            'coursemember__user_id',
            filter=Q(coursemember__user_id__is_superuser=False),
            distinct=True
        )
    ).order_by('-member_count')[:3]

    recent_comments = Comment.objects.select_related(
        'member_id__user_id', 'content_id'
    ).order_by('-created_at')[:5]

    recent_joins = CourseMember.objects.select_related(
        'user_id', 'course_id'
    ).exclude(user_id__is_superuser=True).order_by('-created_at')[:5]

    activities = []

    for c in recent_comments:
        if c.content_id:
            text = f'berkomentar di "{c.content_id.name}"'
        else:
            text = f'memulai diskusi "{c.title}"' if c.title else 'memulai topik diskusi baru'

        activities.append({
            'username': c.member_id.user_id.username,
            'text': text,
            'time': c.created_at,
        })

    for m in recent_joins:
        activities.append({
            'username': m.user_id.username,
            'text': f'bergabung sebagai member "{m.course_id.name}"',
            'time': m.created_at,
        })

    activities.sort(key=lambda a: a['time'], reverse=True)
    activities = activities[:5]

    avg_price = Course.objects.aggregate(avg=Avg('price'))['avg']

    context = {
        'active_page': 'dashboard',
        'user_count': total_users,
        'course_count': total_courses,
        'member_count': total_members,
        'avg_price': int(avg_price) if avg_price else 0,
        'popular_courses': popular_courses,
        'activities': activities,
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
@login_required
def comment_list(request):

    is_admin_user = request.user.is_staff or request.user.is_superuser
    tab = request.GET.get('tab', 'qa')

    if request.method == 'POST':
        action = request.POST.get('action', 'post_topic')

        if action == 'reply':
            # 🔥 balasan admin/pengajar atas pertanyaan diskusi siswa pada
            # suatu materi — disimpan ke tabel CommentReply (terpisah dari
            # Comment) karena admin belum tentu punya baris CourseMember.
            comment_id = request.POST.get('comment_id')
            reply_text = request.POST.get('reply', '').strip()
            if reply_text and is_admin_user:
                comment = get_object_or_404(Comment, pk=comment_id)
                CommentReply.objects.create(comment=comment, admin=request.user, text=reply_text)
                messages.success(request, 'Balasan berhasil dikirim.')
            return redirect('/comments/?tab=qa')

        # Topik diskusi umum (fitur lama) = komentar yang tidak terikat ke
        # konten tertentu maupun ulasan kursus.
        title = request.POST.get('title', '').strip()
        comment_text = request.POST.get('comment', '').strip()
        member = CourseMember.objects.filter(user_id=request.user).first()

        if member and comment_text:
            Comment.objects.create(
                title=title,
                comment=comment_text,
                member_id=member,
                content_id=None
            )

        return redirect('/comments/?tab=general')

    search_query = request.GET.get('search', '').strip()

    # Tab "Tanya Jawab Materi": diskusi siswa per konten/video, lengkap
    # dengan balasan admin (CommentReply) supaya admin bisa menjawab.
    qa_comments = Comment.objects.select_related(
        'member_id__user_id', 'content_id__course'
    ).prefetch_related('replies__admin').filter(content_id__isnull=False)

    # Tab "Ulasan Kursus": ulasan bintang yang dikirim siswa lewat halaman
    # course_detail (action='review') — read-only di sisi admin.
    review_comments = Comment.objects.select_related(
        'member_id__user_id', 'course'
    ).filter(rating__isnull=False).order_by('-created_at')

    # Tab "Diskusi Umum": fitur lama, tidak terikat konten/ulasan.
    general_comments = Comment.objects.select_related(
        'member_id__user_id'
    ).filter(content_id__isnull=True, rating__isnull=True, course__isnull=True)

    if search_query:
        qa_comments = qa_comments.filter(
            Q(member_id__user_id__username__icontains=search_query) |
            Q(comment__icontains=search_query) |
            Q(content_id__name__icontains=search_query)
        )
        general_comments = general_comments.filter(
            Q(member_id__user_id__username__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(comment__icontains=search_query)
        )

    qa_comments = qa_comments.order_by('-created_at')
    general_comments = general_comments.order_by('-created_at')

    recent_videos = CourseContent.objects.filter(
        Q(video_url__isnull=False) & ~Q(video_url='') | Q(video_file__isnull=False) & ~Q(video_file='')
    ).order_by('-created_at')[:3]

    return render(request, 'lms/comment_list.html', {
        'active_page': 'discussions',
        'tab': tab,
        'qa_comments': qa_comments,
        'review_comments': review_comments,
        'comments': general_comments,
        'recent_videos': recent_videos,
        'search_query': search_query,
        'is_admin_user': is_admin_user,
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
# LIST CONTENT (dikelompokkan per course, setiap materi tampil sebagai Part)
# =========================
@login_required
def content_list(request, id=None):

    if id:
        single = get_object_or_404(CourseContent.objects.select_related('course'), pk=id)
        course_groups = [{'course': single.course, 'parts': [single]}]
    else:
        courses = Course.objects.filter(contents__isnull=False).distinct().prefetch_related('contents').order_by('-created_at')
        course_groups = [
            {'course': c, 'parts': list(c.contents.order_by('id'))}
            for c in courses
        ]

    return render(request, 'lms/content_list.html', {
        'active_page': 'video_file',
        'course_groups': course_groups,
        'single_content': bool(id),
    })

# =========================
# ADD CONTENT (= tambah Part Video baru untuk sebuah course)
# =========================
@login_required
def add_content(request):
    preselected_course_id = request.POST.get('course') or request.GET.get('course')

    if request.method == 'POST':
        video_url = request.POST.get('video_url')
        video_url = clean_youtube_url(video_url)  # 🔥 FIX UTAMA

        CourseContent.objects.create(
            name=request.POST.get('name'),
            description=request.POST.get('description', ''),
            video_url=video_url,
            video_file=request.FILES.get('video_file'),
            file_attachment=request.FILES.get('file_attachment'),
            course_id=preselected_course_id,
        )

        # 🔥 kalau datang dari Course Management (course sudah dipilih),
        # balik ke situ supaya admin langsung lihat daftar part terbaru.
        if preselected_course_id:
            return redirect(f'/courses/create/?edit={preselected_course_id}#parts')
        return redirect('/content/')

    courses = Course.objects.all()
    preselected_course = None
    if preselected_course_id:
        preselected_course = Course.objects.filter(pk=preselected_course_id).first()

    return render(request, 'lms/add_content.html', {
        'courses': courses,
        'preselected_course': preselected_course,
    })


# =========================
# DELETE CONTENT (= hapus satu Part Video dari course)
# =========================
@login_required
def delete_content_view(request, id):
    if request.method == 'POST':
        content = get_object_or_404(CourseContent, pk=id)
        course_id = content.course_id
        name = content.name
        try:
            content.delete()
            messages.success(request, f'🗑️ Part "{name}" berhasil dihapus.')
        except RestrictedError:
            messages.error(
                request,
                f'❌ Part "{name}" tidak bisa dihapus karena masih memiliki sub-materi.'
            )
        return redirect(f'/courses/create/?edit={course_id}#parts')
    return redirect('/courses/create/')
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

@login_required
def course_dashboard_stat(request):
    # =========================
    # BASIC
    # =========================
    total_course = Course.objects.count()
    total_user = User.objects.filter(is_superuser=False).count()
    total_comment = Comment.objects.count()
    today_comment_count = Comment.objects.filter(
        created_at__date=timezone.now().date()
    ).count()

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
    # Pakai 'coursemember__user_id' (bukan 'coursemember') supaya distinct
    # menghitung user unik, bukan baris CourseMember unik — user yang
    # terdaftar dobel di course yang sama tidak akan dihitung dua kali.
    popular_courses = Course.objects.annotate(
        member_count=Count(
            'coursemember__user_id',
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
    # COURSE TERPOPULER (UNTUK CARD DETAIL)
    # =========================
    top_course = popular_courses.first()
    max_content_count = max(
        [c.content_count for c in content_stats], default=0
    ) or 1

    # =========================
    # CONTEXT
    # =========================
    context = {
        'active_page': 'statistics',
        'total_course': total_course,
        'total_member': total_member,
        'total_user': total_user,
        'total_comment': total_comment,
        'today_comment_count': today_comment_count,
        'avg_price': int(price_stats['avg_price']) if price_stats['avg_price'] else 0,
        'max_price': price_stats['max_price'] or 0,
        'min_price': price_stats['min_price'] or 0,

        'popular_courses': popular_courses,
        'top_course': top_course,
        'cheapest_courses': cheapest_courses,
        'expensive_courses': expensive_courses,
        'content_stats': content_stats,
        'comment_stats': comment_stats,
        'max_content_count': max_content_count,
    }

    return render(request, 'lms/course_dashboard.html', context)


# =========================
# LOGIN
# =========================
def login_view(request):

    if request.user.is_authenticated:
        return redirect(_dashboard_redirect_url(request.user))

    # 🔥 supaya setelah login user dikembalikan ke halaman yang awalnya
    # dia tuju (bukan selalu dilempar ke /dashboard/), sesuai redirect
    # otomatis dari @login_required (?next=...)
    next_url = request.POST.get('next') or request.GET.get('next', '')

    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')
        keep_signed_in = request.POST.get('keep_signed_in') == 'on'

        # 🔥 boleh login pakai username ATAU email. Beberapa akun lama bisa
        # share email yang sama, jadi semua username yang cocok dicoba satu
        # per satu (bukan asal ambil yang pertama) supaya tidak salah akun.
        candidate_usernames = [identifier]
        candidate_usernames += User.objects.filter(
            email__iexact=identifier
        ).values_list('username', flat=True)

        user = None
        for candidate in candidate_usernames:
            user = authenticate(request, username=candidate, password=password)
            if user is not None:
                break

        if user is not None:
            login(request, user)

            if keep_signed_in:
                request.session.set_expiry(60 * 60 * 24 * 14)  # 14 hari
            else:
                request.session.set_expiry(0)  # habis saat browser ditutup

            # 🔥 admin/superuser selalu balik ke dashboard admin lama,
            # apa pun nilai ?next= nya (mis. sempat nyasar ke /learn/).
            # Untuk siswa biasa, next tetap dihormati supaya balik ke
            # halaman kursus yang awalnya dituju.
            if user.is_superuser:
                return redirect('/dashboard/')

            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)

            return redirect(_dashboard_redirect_url(user))

        return render(request, 'lms/login.html', {
            'error': 'Email/username atau password salah',
            'next': next_url,
        })

    return render(request, 'lms/login.html', {'next': next_url})


# =========================
# REGISTER
# =========================
def _generate_unique_username(email, full_name):
    """Bikin username unik otomatis dari email (atau nama) — user tidak
    perlu mikirin username sendiri, sesuai desain form Create Account."""
    base = (email.split('@')[0] if email else '') or full_name.replace(' ', '')
    base = re.sub(r'[^a-zA-Z0-9_]', '', base).lower() or 'user'

    username = base
    suffix = 1
    while User.objects.filter(username=username).exists():
        suffix += 1
        username = f'{base}{suffix}'

    return username


def register_view(request):

    if request.user.is_authenticated:
        return redirect(_dashboard_redirect_url(request.user))

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        agree = request.POST.get('agree') == 'on'

        error = None
        if not full_name or not email or not password:
            error = 'Semua field wajib diisi.'
        elif password != password2:
            error = 'Konfirmasi password tidak cocok.'
        elif len(password) < 8:
            error = 'Password minimal 8 karakter.'
        elif not agree:
            error = 'Kamu harus menyetujui Terms of Service dan Privacy Policy.'
        elif User.objects.filter(email__iexact=email).exists():
            error = 'Email sudah terdaftar.'

        if error:
            return render(request, 'lms/register.html', {'error': error})

        username = _generate_unique_username(email, full_name)
        name_parts = full_name.split(' ', 1)

        User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else ''
        )

        return redirect('/login/')

    return render(request, 'lms/register.html')


# =========================
# LOGOUT
# =========================
def logout_view(request):

    logout(request)

    return redirect('/login/')


# =========================
# GOOGLE OAUTH (login & register pakai akun Google)
# =========================
GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'


def _google_redirect_uri(request):
    return request.build_absolute_uri('/login/google/callback/')


def google_login_start(request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        messages.error(request, 'Login Google belum dikonfigurasi di server.')
        return redirect('/login/')

    # 🔥 state dipakai buat cegah CSRF pada callback OAuth (harus cocok
    # dengan yang tersimpan di session saat user balik dari Google).
    state = secrets.token_urlsafe(24)
    request.session['google_oauth_state'] = state

    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': _google_redirect_uri(request),
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'prompt': 'select_account',
    }
    return redirect(f'{GOOGLE_AUTH_URL}?{urlencode(params)}')


def google_login_callback(request):
    if request.GET.get('error'):
        messages.error(request, 'Login Google dibatalkan.')
        return redirect('/login/')

    state = request.GET.get('state')
    if not state or state != request.session.pop('google_oauth_state', None):
        messages.error(request, 'Sesi login Google tidak valid, silakan coba lagi.')
        return redirect('/login/')

    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Login Google gagal, kode otorisasi tidak ditemukan.')
        return redirect('/login/')

    token_resp = requests.post(GOOGLE_TOKEN_URL, data={
        'code': code,
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'redirect_uri': _google_redirect_uri(request),
        'grant_type': 'authorization_code',
    }, timeout=10)

    if not token_resp.ok:
        messages.error(request, 'Login Google gagal saat menukar token, coba lagi.')
        return redirect('/login/')

    access_token = token_resp.json().get('access_token')

    userinfo_resp = requests.get(
        GOOGLE_USERINFO_URL,
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=10,
    )
    if not userinfo_resp.ok:
        messages.error(request, 'Login Google gagal mengambil data profil, coba lagi.')
        return redirect('/login/')

    profile = userinfo_resp.json()
    email = (profile.get('email') or '').strip().lower()
    if not email:
        messages.error(request, 'Akun Google tidak memiliki email, tidak bisa login.')
        return redirect('/login/')

    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        full_name = profile.get('name', '').strip()
        username = _generate_unique_username(email, full_name)
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=profile.get('given_name', ''),
            last_name=profile.get('family_name', ''),
        )
        # 🔥 akun via Google tidak punya password lokal — login biasa
        # (username/password) untuk akun ini otomatis tidak akan pernah cocok.
        user.set_unusable_password()
        user.save()

    login(request, user)

    if user.is_superuser:
        return redirect('/dashboard/')
    return redirect(_dashboard_redirect_url(user))


# =========================
# FORGOT / RESET PASSWORD
# =========================
def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect(_dashboard_redirect_url(request.user))

    sent = False

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()

        if user is not None and user.has_usable_password():
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = request.build_absolute_uri(f'/reset-password/{uid}/{token}/')

            send_mail(
                subject='Reset Password — Sagara Course',
                message=(
                    f'Halo {user.first_name or user.username},\n\n'
                    f'Kami menerima permintaan reset password untuk akun Sagara Course-mu.\n'
                    f'Klik link berikut untuk membuat password baru (link berlaku sementara):\n\n'
                    f'{reset_link}\n\n'
                    f'Kalau kamu tidak meminta ini, abaikan saja email ini.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

        # 🔥 selalu tampilkan pesan "terkirim" walau email tidak ditemukan,
        # supaya tidak bisa dipakai untuk cek email mana yang terdaftar.
        sent = True

    return render(request, 'lms/forgot_password.html', {'sent': sent})


def reset_password_view(request, uidb64, token):
    if request.user.is_authenticated:
        return redirect(_dashboard_redirect_url(request.user))

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    token_valid = user is not None and default_token_generator.check_token(user, token)

    if not token_valid:
        return render(request, 'lms/reset_password.html', {'token_valid': False})

    error = None
    if request.method == 'POST':
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        if len(password) < 8:
            error = 'Password minimal 8 karakter.'
        elif password != password2:
            error = 'Konfirmasi password tidak cocok.'
        else:
            user.set_password(password)
            user.save()
            messages.success(request, 'Password berhasil diubah. Silakan login dengan password baru.')
            return redirect('/login/')

    return render(request, 'lms/reset_password.html', {
        'token_valid': True,
        'error': error,
    })


# =========================
# COURSES API v2 (Search, Sort, Pagination)
# =========================
def courses_api_view(request):
    return render(request, 'lms/courses_api.html')


# =========================
# COURSE LIST (tabel: search + sort + pagination)
# =========================
@login_required
def course_list_view(request):
    search_query = request.GET.get('search', '').strip()
    sort = request.GET.get('sort', '-id')
    per_page = request.GET.get('per_page', '10')

    courses = Course.objects.select_related('teacher').all()

    if search_query:
        courses = courses.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(teacher__username__icontains=search_query)
        )

    valid_sorts = {'id', '-id', 'name', '-name', 'price', '-price'}
    if sort not in valid_sorts:
        sort = '-id'
    courses = courses.order_by(sort)

    try:
        per_page = int(per_page)
        if per_page not in (10, 25, 50):
            per_page = 10
    except ValueError:
        per_page = 10

    paginator = Paginator(courses, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'lms/course_list.html', {
        'active_page': 'course_list',
        'page_obj': page_obj,
        'search_query': search_query,
        'sort': sort,
        'per_page': per_page,
        'total_count': paginator.count,
    })


# =========================
# QUICK ACTIONS / DJANGO SYSTEM DASHBOARD
# Semua metrik di bawah diambil dari data riil (django-silk profiling
# & resource module bawaan Python) -- tidak ada angka yang di-hardcode.
# =========================
@login_required
def quick_actions_view(request):
    import resource
    from silk.models import Request as SilkRequest

    silk_stats = SilkRequest.objects.aggregate(
        avg_time=Avg('time_taken'),
        avg_sql=Avg('num_sql_queries'),
        total=Count('id'),
    )

    recent_requests = []
    for r in SilkRequest.objects.order_by('-start_time')[:8]:
        try:
            status_code = r.response.status_code
        except Exception:
            status_code = None

        recent_requests.append({
            'path': r.path,
            'method': r.method,
            'num_sql_queries': r.num_sql_queries,
            'time_taken': r.time_taken,
            'status_code': status_code,
        })

    # Memory usage proses saat ini (RSS), didapat dari modul `resource`
    # bawaan Python -- bukan angka dummy.
    mem_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    memory_mb = round(mem_kb / 1024, 1)

    context = {
        'active_page': 'quick_actions',
        'django_version': django.get_version(),
        'avg_response_time': round(silk_stats['avg_time'], 1) if silk_stats['avg_time'] else 0,
        'avg_sql_queries': round(silk_stats['avg_sql'], 2) if silk_stats['avg_sql'] else 0,
        'total_requests': silk_stats['total'],
        'memory_mb': memory_mb,
        'recent_requests': recent_requests,
        'debug_mode': settings.DEBUG,
    }

    return render(request, 'lms/quick_actions.html', context)


# =========================
# STUDENT PORTAL
# =========================
def _course_progress(membership):
    """Hitung (selesai, total, persen) materi yang sudah ditandai selesai
    oleh membership ini pada course terkait."""
    total = membership.course_id.contents.count()
    done = ContentProgress.objects.filter(
        member=membership,
        content__course=membership.course_id
    ).count()
    percent = round(done / total * 100) if total else 0
    return done, total, percent


# =========================
# CERTIFICATE (PDF sertifikat setelah course selesai 100%)
# =========================
def _generate_certificate_code():
    # 🔥 format "SGR-2026-001", urut per tahun, biar mirip nomor sertifikat asli
    year = timezone.now().year
    seq = Certificate.objects.filter(issued_at__year=year).count() + 1
    return f"SGR-{year}-{seq:03d}"


def _letter_spaced(text, gap=' '):
    """'SERTIFIKAT' -> 'S E R T I F I K A T' — reportlab base fonts tidak
    punya letter-spacing asli, jadi disisipi spasi tipis di antar huruf."""
    return gap.join(list(text))


def _draw_graduation_cap(c, cx, cy, size, color):
    """Gambar ikon topi toga sederhana (diamond + pita kepala + tali rumbai)
    pakai primitif vector reportlab, tanpa perlu file gambar eksternal."""
    c.saveState()
    c.setFillColor(color)
    c.setStrokeColor(color)

    half_w = size / 2
    half_h = size * 0.22

    path = c.beginPath()
    path.moveTo(cx, cy + half_h)
    path.lineTo(cx + half_w, cy)
    path.lineTo(cx, cy - half_h)
    path.lineTo(cx - half_w, cy)
    path.close()
    c.drawPath(path, fill=1, stroke=0)

    band_w = size * 0.46
    band_h = size * 0.22
    c.ellipse(cx - band_w / 2, cy - half_h - band_h * 0.7, cx + band_w / 2, cy - half_h + band_h * 0.3, fill=1, stroke=0)

    c.setLineWidth(size * 0.05)
    tip_x, tip_y = cx + half_w * 0.5, cy - half_h - band_h * 1.1
    c.line(cx + half_w * 0.1, cy + half_h * 0.05, tip_x, tip_y)
    c.circle(tip_x, tip_y, size * 0.05, fill=1, stroke=0)

    c.restoreState()


def _draw_check_seal(c, cx, cy, radius, seal_color, check_color):
    """Lencana bulat kecil dengan tanda centang, mirip stempel keaslian."""
    c.saveState()
    c.setFillColor(seal_color)
    c.circle(cx, cy, radius, fill=1, stroke=0)

    c.setStrokeColor(check_color)
    c.setLineWidth(radius * 0.22)
    c.setLineCap(1)
    path = c.beginPath()
    path.moveTo(cx - radius * 0.45, cy - radius * 0.05)
    path.lineTo(cx - radius * 0.1, cy - radius * 0.4)
    path.lineTo(cx + radius * 0.5, cy + radius * 0.35)
    c.drawPath(path, fill=0, stroke=1)
    c.restoreState()


def _draw_corner_accent(c, x, y, dx, dy, length, color):
    """Garis siku dekoratif di satu sudut sertifikat (dx/dy menentukan arah)."""
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(1.1)
    c.line(x, y, x + dx * length, y)
    c.line(x, y, x, y + dy * length)
    c.restoreState()


def _draw_watermark_pattern(c, width, height, margin):
    """Pola lingkaran tipis berulang sebagai watermark latar belakang."""
    c.saveState()
    c.setFillColor(colors.Color(0.65, 0.68, 0.75, alpha=0.10))
    spacing = 13 * mm
    radius = 4.2 * mm
    y = margin + spacing / 2
    row = 0
    while y < height - margin:
        offset = (spacing / 2) if row % 2 else 0
        x = margin + spacing / 2 + offset
        while x < width - margin:
            c.circle(x, y, radius, fill=1, stroke=0)
            x += spacing
        y += spacing
        row += 1
    c.restoreState()


def _draw_qr(c, data, x, y, size):
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF

    widget = QrCodeWidget(data)
    b = widget.getBounds()
    w = b[2] - b[0]
    h = b[3] - b[1]
    d = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
    d.add(widget)
    renderPDF.draw(d, c, x, y)


def _draw_centered_paragraph(c, html_text, x_center, y_top, max_width, style_kwargs):
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    style = ParagraphStyle('cert', alignment=TA_CENTER, **style_kwargs)
    p = Paragraph(html_text, style)
    w, h = p.wrap(max_width, 60 * mm)
    p.drawOn(c, x_center - w / 2, y_top - h)
    return h


def _build_certificate_pdf(request, student_name, course_name, teacher_name, issued_at, code):
    buffer = BytesIO()
    width, height = landscape(A4)
    c = pdf_canvas.Canvas(buffer, pagesize=landscape(A4))

    navy = colors.HexColor('#1E3A8A')
    ink = colors.HexColor('#111827')
    muted = colors.HexColor('#6b7280')
    gold = colors.HexColor('#a9824c')

    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    margin = 11 * mm
    _draw_watermark_pattern(c, width, height, margin)

    c.setStrokeColor(navy)
    c.setLineWidth(2.4)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin, fill=0, stroke=1)

    corner_len = 16 * mm
    corner_inset = margin + 4 * mm
    _draw_corner_accent(c, corner_inset, height - corner_inset, 1, -1, corner_len, gold)
    _draw_corner_accent(c, width - corner_inset, height - corner_inset, -1, -1, corner_len, gold)
    _draw_corner_accent(c, corner_inset, corner_inset, 1, 1, corner_len, gold)
    _draw_corner_accent(c, width - corner_inset, corner_inset, -1, 1, corner_len, gold)

    cx = width / 2
    y = height - 26 * mm

    badge_r = 6 * mm
    badge_label_w = c.stringWidth('Sagara Course', 'Helvetica-Bold', 15)
    row_w = badge_r * 2 + 4 * mm + badge_label_w
    badge_cx = cx - row_w / 2 + badge_r

    c.setFillColor(navy)
    c.circle(badge_cx, y, badge_r, fill=1, stroke=0)
    _draw_graduation_cap(c, badge_cx, y + 0.3 * mm, badge_r * 1.25, colors.white)

    c.setFillColor(navy)
    c.setFont('Helvetica-Bold', 15)
    c.drawString(badge_cx + badge_r + 4 * mm, y - 5, 'Sagara Course')

    y -= 10 * mm
    c.setStrokeColor(gold)
    c.setLineWidth(1.4)
    c.line(cx - 14 * mm, y, cx + 14 * mm, y)

    y -= 9 * mm
    c.setFillColor(navy)
    c.setFont('Times-Bold', 15)
    c.drawCentredString(cx, y, _letter_spaced('SERTIFIKAT KELULUSAN'))

    y -= 6.5 * mm
    c.setFillColor(muted)
    c.setFont('Helvetica', 9.5)
    c.drawCentredString(cx, y, _letter_spaced('CERTIFICATE OF EXCELLENCE', gap='  '))

    y -= 12 * mm
    c.setFillColor(muted)
    c.setFont('Helvetica', 11)
    c.drawCentredString(cx, y, 'Diberikan kepada:')

    y -= 13 * mm
    c.setFillColor(navy)
    c.setFont('Times-Bold', 27)
    c.drawCentredString(cx, y, student_name)

    y -= 5.5 * mm
    name_w = max(60 * mm, c.stringWidth(student_name, 'Times-Bold', 27) + 14 * mm)
    c.setStrokeColor(gold)
    c.setLineWidth(0.9)
    c.line(cx - name_w / 2, y, cx + name_w / 2, y)

    y -= 9 * mm
    c.setFillColor(muted)
    c.setFont('Helvetica', 10.5)
    c.drawCentredString(cx, y, _letter_spaced('TELAH MENYELESAIKAN KURSUS'))

    y -= 7.5 * mm
    c.setFillColor(navy)
    c.setFont('Helvetica-Bold', 15)
    c.drawCentredString(cx, y, course_name.upper())

    y -= 11 * mm
    paragraph_html = (
        'Selamat atas keberhasilan Anda dalam menyelesaikan kursus ini. '
        'Semoga ilmu yang didapatkan dapat bermanfaat untuk karir dan masa depan.'
    )
    _draw_centered_paragraph(
        c, paragraph_html, cx, y, 165 * mm,
        {'fontName': 'Helvetica', 'fontSize': 10.5, 'leading': 15, 'textColor': ink}
    )

    # =========================
    # BARIS BAWAH: tanggal | QR + ID | tanda tangan
    # =========================
    base_y = margin + 20 * mm
    left_x = margin + 28 * mm
    right_x = width - margin - 30 * mm

    c.setStrokeColor(muted)
    c.setLineWidth(0.6)
    c.line(left_x - 20 * mm, base_y + 11 * mm, left_x + 20 * mm, base_y + 11 * mm)
    c.setFillColor(muted)
    c.setFont('Helvetica', 8.5)
    c.drawCentredString(left_x, base_y + 6 * mm, _letter_spaced('TANGGAL TERBIT'))
    c.setFillColor(ink)
    c.setFont('Helvetica-Bold', 11)
    c.drawCentredString(left_x, base_y, issued_at.strftime('%d %B %Y'))

    qr_size = 17 * mm
    verify_url = request.build_absolute_uri(f'/sertifikat/verifikasi/{code}/')
    _draw_qr(c, verify_url, cx - qr_size / 2, base_y - 1 * mm, qr_size)
    c.setFillColor(muted)
    c.setFont('Helvetica', 8.5)
    c.drawCentredString(cx, base_y - 5 * mm, f'ID: {code}')

    c.setFillColor(navy)
    c.setFont('Times-Italic', 16)
    c.drawCentredString(right_x, base_y + 10 * mm, teacher_name)
    _draw_check_seal(c, right_x + 22 * mm, base_y + 16 * mm, 4 * mm, colors.HexColor('#e5e7eb'), navy)

    c.setStrokeColor(muted)
    c.setLineWidth(0.6)
    c.line(right_x - 20 * mm, base_y + 6 * mm, right_x + 20 * mm, base_y + 6 * mm)
    c.setFillColor(ink)
    c.setFont('Helvetica-Bold', 10.5)
    c.drawCentredString(right_x, base_y, teacher_name)
    c.setFillColor(muted)
    c.setFont('Helvetica', 8.5)
    c.drawCentredString(right_x, base_y - 5 * mm, 'Pengajar, Sagara Course')

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


@login_required
def download_certificate_view(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    membership = get_object_or_404(CourseMember, user_id=request.user, course_id=course)

    _, total, percent = _course_progress(membership)
    if total == 0 or percent < 100:
        messages.error(request, 'Selesaikan semua materi course ini terlebih dahulu untuk mendapatkan sertifikat.')
        return redirect(f'/learn/courses/{course.id}/')

    certificate, _ = Certificate.objects.get_or_create(
        member=membership,
        defaults={'code': _generate_certificate_code()},
    )

    student_name = request.user.get_full_name() or request.user.username
    teacher_name = course.teacher.get_full_name() or course.teacher.username

    buffer = _build_certificate_pdf(
        request,
        student_name=student_name,
        course_name=course.name,
        teacher_name=teacher_name,
        issued_at=certificate.issued_at,
        code=certificate.code,
    )

    filename = f"Sertifikat - {course.name} - {student_name}.pdf".replace('/', '-')
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def certificate_verify_view(request, code):
    certificate = Certificate.objects.select_related(
        'member__user_id', 'member__course_id__teacher'
    ).filter(code=code).first()
    return render(request, 'lms/certificate_verify.html', {
        'certificate': certificate,
        'code': code,
    })


def _flatten_contents(course):
    """Urutan materi datar: modul (parent kosong) lalu anak-anaknya,
    dipakai untuk menentukan materi 'selanjutnya' di lesson player."""
    flat = []
    modules = course.contents.filter(parent__isnull=True).order_by('id').prefetch_related('children')
    for module in modules:
        flat.append(module)
        for child in module.children.order_by('id'):
            flat.append(child)
    return flat


def _annotate_course_stats(queryset):
    """Tambah avg_rating, review_count, student_count per course supaya
    card kursus bisa tampilkan rating & jumlah siswa tanpa query tambahan."""
    return queryset.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews', filter=Q(reviews__rating__isnull=False), distinct=True),
        student_count=Count('coursemember__user_id', distinct=True),
    )


def _attach_price_fmt(courses):
    for c in courses:
        c.price_fmt = _price_fmt(c.price)
    return courses


@login_required
def student_dashboard(request):
    memberships = CourseMember.objects.filter(
        user_id=request.user
    ).select_related('course_id').order_by('-created_at')

    my_courses = []
    percents = []
    continue_learning = None

    for m in memberships:
        done, total, percent = _course_progress(m)
        my_courses.append({
            'membership': m,
            'course': m.course_id,
            'done': done,
            'total': total,
            'percent': percent,
        })
        percents.append(percent)

        if continue_learning is None:
            flat = _flatten_contents(m.course_id)
            completed_ids = set(ContentProgress.objects.filter(
                member=m, content__course=m.course_id
            ).values_list('content_id', flat=True))
            next_content = next((c for c in flat if c.id not in completed_ids), None)
            if next_content:
                continue_learning = {'course': m.course_id, 'content': next_content}

    overall_percent = round(sum(percents) / len(percents)) if percents else 0

    enrolled_ids = [m.course_id_id for m in memberships]
    recommended = _attach_price_fmt(_annotate_course_stats(
        Course.objects.select_related('teacher').exclude(id__in=enrolled_ids)
    ).order_by('-created_at')[:4])

    return render(request, 'lms/student_dashboard.html', {
        'active_page': 'student_dashboard',
        'my_courses': my_courses,
        'overall_percent': overall_percent,
        'continue_learning': continue_learning,
        'recommended': recommended,
    })


@login_required
def student_courses(request):
    memberships = CourseMember.objects.filter(
        user_id=request.user
    ).select_related('course_id').order_by('-created_at')

    my_courses = []
    for m in memberships:
        done, total, percent = _course_progress(m)
        my_courses.append({
            'membership': m,
            'course': m.course_id,
            'done': done,
            'total': total,
            'percent': percent,
        })

    enrolled_ids = [m.course_id_id for m in memberships]
    recommended = _attach_price_fmt(_annotate_course_stats(
        Course.objects.select_related('teacher').exclude(id__in=enrolled_ids)
    ).order_by('-created_at')[:4])

    return render(request, 'lms/student_courses.html', {
        'active_page': 'student_courses',
        'my_courses': my_courses,
        'recommended': recommended,
    })


@login_required
def course_catalog(request):
    if request.method == 'POST' and request.POST.get('action') == 'enroll':
        quick_course = get_object_or_404(Course, pk=request.POST.get('course_id'))
        CourseMember.objects.get_or_create(user_id=request.user, course_id=quick_course)
        messages.success(request, f'Berhasil mendaftar ke "{quick_course.name}".')
        return redirect(request.get_full_path())

    search_query = request.GET.get('search', '').strip()
    category = request.GET.get('category', 'all')
    sort = request.GET.get('sort', 'terbaru')

    courses = _annotate_course_stats(Course.objects.select_related('teacher'))

    if search_query:
        courses = courses.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    if category != 'all':
        courses = courses.filter(category=category)

    if sort == 'harga_asc':
        courses = courses.order_by('price')
    elif sort == 'harga_desc':
        courses = courses.order_by('-price')
    else:
        courses = courses.order_by('-created_at')

    paginator = Paginator(courses, 8)
    page_obj = paginator.get_page(request.GET.get('page'))
    _attach_price_fmt(page_obj)

    enrolled_ids = set(CourseMember.objects.filter(
        user_id=request.user
    ).values_list('course_id_id', flat=True))

    return render(request, 'lms/course_catalog.html', {
        'active_page': 'student_catalog',
        'page_obj': page_obj,
        'categories': COURSE_CATEGORIES,
        'active_category': category,
        'search_query': search_query,
        'sort': sort,
        'enrolled_ids': enrolled_ids,
        'showing_start': page_obj.start_index(),
        'showing_end': page_obj.end_index(),
        'total_count': paginator.count,
    })


@login_required
def course_detail(request, id):
    course = get_object_or_404(
        _annotate_course_stats(Course.objects.select_related('teacher')), pk=id
    )
    course.price_fmt = _price_fmt(course.price)
    membership = CourseMember.objects.filter(user_id=request.user, course_id=course).first()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'enroll':
            CourseMember.objects.get_or_create(user_id=request.user, course_id=course)
            messages.success(request, f'Berhasil mendaftar ke "{course.name}".')

        elif action == 'review' and membership:
            rating = request.POST.get('rating')
            review_text = request.POST.get('comment', '').strip()
            if not rating:
                messages.error(request, 'Pilih rating bintang terlebih dahulu sebelum mengirim ulasan.')
            elif not review_text:
                messages.error(request, 'Tulis komentar ulasan terlebih dahulu sebelum mengirim.')
            else:
                Comment.objects.create(
                    course=course,
                    member_id=membership,
                    rating=int(rating),
                    comment=review_text,
                )
                messages.success(request, 'Terima kasih atas ulasannya!')

        return redirect(f'/learn/courses/{course.id}/')

    modules = course.contents.filter(parent__isnull=True).order_by('id').prefetch_related('children')
    total_content = course.contents.count()

    done = 0
    if membership:
        done = ContentProgress.objects.filter(member=membership, content__course=course).count()
    percent = round(done / total_content * 100) if total_content else 0

    trailer_content = course.contents.filter(
        Q(video_file__isnull=False) & ~Q(video_file='') | Q(video_url__isnull=False) & ~Q(video_url='')
    ).order_by('id').first()

    reviews = course.reviews.select_related('member_id__user_id').filter(
        rating__isnull=False
    ).order_by('-created_at')

    next_content = None
    completed_ids = set()
    if membership:
        flat = _flatten_contents(course)
        completed_ids = set(ContentProgress.objects.filter(
            member=membership, content__course=course
        ).values_list('content_id', flat=True))
        next_content = next((c for c in flat if c.id not in completed_ids), flat[0] if flat else None)

    return render(request, 'lms/course_detail.html', {
        'active_page': 'student_catalog',
        'course': course,
        'membership': membership,
        'modules': modules,
        'completed_ids': completed_ids,
        'total_content': total_content,
        'done': done,
        'percent': percent,
        'trailer_content': trailer_content,
        'reviews': reviews,
        'avg_rating': course.avg_rating or 0,
        'next_content': next_content,
    })


@login_required
def lesson_player(request, course_id, content_id):
    course = get_object_or_404(Course, pk=course_id)
    membership = CourseMember.objects.filter(user_id=request.user, course_id=course).first()

    if not membership:
        messages.error(request, 'Anda belum terdaftar di course ini.')
        return redirect(f'/learn/courses/{course.id}/')

    content = get_object_or_404(CourseContent, pk=content_id, course=course)
    flat = _flatten_contents(course)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'complete':
            ContentProgress.objects.get_or_create(member=membership, content=content)

            idx = next((i for i, c in enumerate(flat) if c.id == content.id), None)
            next_item = flat[idx + 1] if idx is not None and idx + 1 < len(flat) else None

            if next_item:
                return redirect(f'/learn/courses/{course.id}/learn/{next_item.id}/')
            return redirect(f'/learn/courses/{course.id}/')

        elif action == 'note':
            text = request.POST.get('text', '').strip()
            if text:
                Note.objects.update_or_create(
                    member=membership, content=content,
                    defaults={'text': text}
                )
            return redirect(f'/learn/courses/{course.id}/learn/{content.id}/?tab=catatan')

        elif action == 'comment':
            comment_text = request.POST.get('comment', '').strip()
            if comment_text:
                Comment.objects.create(
                    content_id=content,
                    member_id=membership,
                    comment=comment_text,
                )
            return redirect(f'/learn/courses/{course.id}/learn/{content.id}/?tab=diskusi')

    modules = course.contents.filter(parent__isnull=True).order_by('id').prefetch_related('children')
    completed_ids = set(ContentProgress.objects.filter(
        member=membership, content__course=course
    ).values_list('content_id', flat=True))

    my_note = Note.objects.filter(member=membership, content=content).first()
    comments = content.comments.select_related('member_id__user_id').order_by('-created_at')

    tab = request.GET.get('tab', 'deskripsi')

    idx = next((i for i, c in enumerate(flat) if c.id == content.id), None)
    prev_content = flat[idx - 1] if idx is not None and idx > 0 else None

    total_content = len(flat)
    done_count = len(completed_ids)
    course_percent = round(done_count / total_content * 100) if total_content else 0

    return render(request, 'lms/lesson_player.html', {
        'active_page': 'student_catalog',
        'course': course,
        'content': content,
        'modules': modules,
        'completed_ids': completed_ids,
        'my_note': my_note,
        'comments': comments,
        'tab': tab,
        'prev_content': prev_content,
        'total_content': total_content,
        'done_count': done_count,
        'course_percent': course_percent,
    })


# =========================
# PUBLIC LANDING (localhost:8000)
# =========================
def landing_view(request):
    if request.user.is_authenticated:
        return redirect(_dashboard_redirect_url(request.user))

    featured_courses = _attach_price_fmt(list(_annotate_course_stats(
        Course.objects.select_related('teacher')
    ).order_by('-student_count', '-avg_rating')[:4]))

    total_students = User.objects.filter(coursemember__isnull=False).distinct().count()
    total_courses = Course.objects.count()
    total_mentors = User.objects.filter(course__isnull=False).distinct().count()
    avg_platform_rating = Comment.objects.filter(rating__isnull=False).aggregate(v=Avg('rating'))['v'] or 0

    price_stats = Course.objects.aggregate(min_price=Min('price'), max_price=Max('price'))
    min_price_fmt = _price_fmt(price_stats['min_price'] or 0)
    max_price_fmt = _price_fmt(price_stats['max_price'] or 0)

    mentors = User.objects.filter(
        Q(is_staff=True) | Q(is_superuser=True)
    ).distinct().annotate(course_count=Count('course', distinct=True))

    return render(request, 'lms/landing.html', {
        'featured_courses': featured_courses,
        'total_students': total_students,
        'total_courses': total_courses,
        'total_mentors': total_mentors,
        'avg_platform_rating': avg_platform_rating,
        'min_price_fmt': min_price_fmt,
        'max_price_fmt': max_price_fmt,
        'mentors': mentors,
    })


def privacy_policy_view(request):
    return render(request, 'lms/privacy_policy.html')


def terms_of_service_view(request):
    return render(request, 'lms/terms_of_service.html')


def careers_view(request):
    img_dir = settings.BASE_DIR / 'static' / 'img'
    company_logos = sorted(
        f.name for f in img_dir.iterdir()
        if f.is_file() and f.name != 'bg-hero.png'
    ) if img_dir.exists() else []

    return render(request, 'lms/careers.html', {'company_logos': company_logos})


@login_required
def coming_soon(request, feature):
    return render(request, 'lms/coming_soon.html', {
        'active_page': 'student_dashboard',
        'feature': feature,
    })
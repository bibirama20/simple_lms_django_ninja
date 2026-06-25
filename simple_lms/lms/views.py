import django
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Max, Min, Avg, Count, Q
from django.db.models.deletion import RestrictedError
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
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

        if course_id:
            course = get_object_or_404(Course, pk=course_id)
            course.name = request.POST['name']
            course.description = request.POST['description']
            course.price = int(request.POST['price'])
            course.teacher = User.objects.get(pk=request.POST['teacher'])
            course.save()

            if youtube_url or materi_pdf:
                content = course.contents.first()
                if content:
                    if youtube_url:
                        content.video_url = youtube_url
                    if materi_pdf:
                        content.file_attachment = materi_pdf
                    content.save()
                else:
                    CourseContent.objects.create(
                        name=f"Materi Pengantar - {course.name}",
                        course=course,
                        video_url=youtube_url,
                        file_attachment=materi_pdf
                    )

            messages.success(request, f'✅ Course "{course.name}" berhasil diperbarui.')
        else:
            course = Course.objects.create(
                name=request.POST['name'],
                description=request.POST['description'],
                price=int(request.POST['price']),
                teacher=User.objects.get(pk=request.POST['teacher'])
            )

            if youtube_url or materi_pdf:
                CourseContent.objects.create(
                    name=f"Materi Pengantar - {course.name}",
                    course=course,
                    video_url=youtube_url,
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

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        comment_text = request.POST.get('comment', '').strip()

        # 🔥 sementara ambil member pertama (belum ada session member resmi)
        member = CourseMember.objects.first()

        if member and comment_text:
            Comment.objects.create(
                title=title,
                comment=comment_text,
                member_id=member,
                content_id=None
            )

        return redirect('/comments/')

    search_query = request.GET.get('search', '').strip()

    # Topik diskusi umum = komentar yang tidak terikat ke konten tertentu
    comments = Comment.objects.select_related(
        'member_id__user_id',
        'content_id'
    ).filter(content_id__isnull=True)

    if search_query:
        comments = comments.filter(
            Q(member_id__user_id__username__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(comment__icontains=search_query)
        )

    comments = comments.order_by('-created_at')

    recent_videos = CourseContent.objects.exclude(
        video_url__isnull=True
    ).exclude(video_url='').order_by('-created_at')[:3]

    return render(request, 'lms/comment_list.html', {
        'active_page': 'discussions',
        'comments': comments,
        'recent_videos': recent_videos,
        'search_query': search_query,
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
@login_required
def content_list(request, id=None):

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

        return redirect(f'/content/{id}/' if id else '/content/')

    # =========================
    # AMBIL CONTENT + KOMENTAR
    # =========================
    if id:
        contents = [get_object_or_404(
            CourseContent.objects.prefetch_related('comments__member_id__user_id'),
            pk=id
        )]
    else:
        contents = CourseContent.objects.prefetch_related(
            'comments__member_id__user_id'
        ).all()

    return render(request, 'lms/content_list.html', {
        'active_page': 'video_file',
        'contents': contents,
        'single_content': bool(id),
    })

# =========================
# ADD CONTENT
# =========================
@login_required
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
        return redirect('/dashboard/')

    # 🔥 supaya setelah login user dikembalikan ke halaman yang awalnya
    # dia tuju (bukan selalu dilempar ke /dashboard/), sesuai redirect
    # otomatis dari @login_required (?next=...)
    next_url = request.POST.get('next') or request.GET.get('next', '')

    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')
        keep_signed_in = request.POST.get('keep_signed_in') == 'on'

        # 🔥 boleh login pakai username ATAU email
        username = identifier
        user_by_email = User.objects.filter(email__iexact=identifier).first()
        if user_by_email:
            username = user_by_email.username

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if keep_signed_in:
                request.session.set_expiry(60 * 60 * 24 * 14)  # 14 hari
            else:
                request.session.set_expiry(0)  # habis saat browser ditutup

            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)

            return redirect('/dashboard/')

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
        return redirect('/dashboard/')

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

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else ''
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
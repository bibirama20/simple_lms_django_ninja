from ninja import NinjaAPI, Schema
from ninja.throttling import AnonRateThrottle, AuthRateThrottle

from ninja_simple_jwt.auth.views.api import mobile_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth

from .models import Course
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from .models import CourseContent
from .models import Comment
from .models import CourseMember
from django.db.models import Count, Avg, Max, Min
from pydantic import field_validator

apiv1 = NinjaAPI(
    title="LMS API",
    version="1.0",
    throttle=[
        AnonRateThrottle('10/m'),
        AuthRateThrottle('100/m'),
    ],
)

apiv1.add_router("/auth/", mobile_auth_router)

apiAuth = HttpJwtAuth()

# =========================
# SCHEMA COURSE
# =========================
class CourseSchema(Schema):
    name: str
    description: str
    price: int
    teacher_id: int = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, value):

        if len(value) < 5:
            raise ValueError("Nama course minimal 5 karakter")

        return value

    @field_validator('price')
    @classmethod
    def validate_price(cls, value):

        if value < 10000:
            raise ValueError("Harga minimal 10000")

        return value


# =========================
# SCHEMA COMMENT
# =========================
class CommentSchema(Schema):
    content_id: int
    comment: str


# =========================
# TEST API
# =========================
@apiv1.get("/hello", auth=None)
def hello(request):

    return {
        "message": "Hello Django Ninja"
    }


# =========================
# HELLO API USERS
# =========================
@apiv1.get("/users/", auth=None)
def hello_users(request):

    users = User.objects.all()

    data = []

    for u in users:
        data.append({
            "id": u.id,
            "username": u.username,
            "email": u.email
        })

    return data


# =========================
# API COURSE
# =========================
@apiv1.get("/courses/", auth=None)
def get_courses(request):

    courses = Course.objects.all()

    data = []

    for c in courses:
        data.append({
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "price": c.price,
            "teacher": c.teacher.username
        })

    return data


# =========================
# GET DETAIL COURSE
# =========================
@apiv1.get("/courses/{course_id}", auth=None)
def detail_course(request, course_id: int):

    c = get_object_or_404(Course, id=course_id)

    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "price": c.price,
        "teacher": c.teacher.username
    }


# =========================
# CREATE COURSE
# =========================
@apiv1.post("/courses/", auth=apiAuth)
def create_course_api(request, payload: CourseSchema):

    if payload.teacher_id:
        teacher = get_object_or_404(User, id=payload.teacher_id)
    else:
        teacher = User.objects.first()

    course = Course.objects.create(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        teacher=teacher
    )

    return {
        "message": "Course berhasil dibuat",
        "course_id": course.id
    }


# =========================
# API UPDATE COURSE (PUT)
# =========================
@apiv1.put("/courses/{course_id}", auth=apiAuth)
def update_course(request, course_id: int, data: CourseSchema):

    course = get_object_or_404(Course, id=course_id)

    course.name = data.name
    course.description = data.description
    course.price = data.price

    if data.teacher_id:
        teacher = get_object_or_404(User, id=data.teacher_id)
        course.teacher = teacher

    course.save()

    return {
        "status": "updated"
    }


# =========================
# API DELETE COURSE
# =========================
@apiv1.delete("/courses/{course_id}", auth=apiAuth)
def delete_course(request, course_id: int):

    course = get_object_or_404(Course, id=course_id)

    course.delete()

    return {
        "status": "deleted"
    }


# =========================
# API COURSE CONTENT
# =========================
@apiv1.get("/contents/", auth=None)
def get_contents(request):

    contents = CourseContent.objects.all()

    data = []

    for c in contents:
        data.append({
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "video_url": c.video_url,
            "course": c.course.name
        })

    return data


# =========================
# API COMMENT
# =========================
@apiv1.get("/comments/", auth=None)
def get_comments(request):

    comments = Comment.objects.all()

    data = []

    for c in comments:
        data.append({
            "id": c.id,
            "comment": c.comment,
            "user": c.member_id.user_id.username
        })

    return data


# =========================
# API COURSE MEMBER
# =========================
@apiv1.get("/members/", auth=None)
def get_members(request):

    members = CourseMember.objects.select_related(
        'course_id',
        'user_id'
    ).all()

    data = []

    for m in members:
        data.append({
            "id": m.id,
            "course": m.course_id.name,
            "user": m.user_id.username,
            "role": m.roles
        })

    return data


# =========================
# API STATISTIK COURSE
# =========================
@apiv1.get("/course-stat/", auth=None)
def course_stat(request):

    stats = Course.objects.aggregate(
        total_course=Count('id'),
        avg_price=Avg('price'),
        max_price=Max('price'),
        min_price=Min('price')
    )

    return {
        "total_course": stats['total_course'],
        "avg_price": stats['avg_price'],
        "max_price": stats['max_price'],
        "min_price": stats['min_price']
    }


# =========================
# API SEARCH COURSE
# =========================
@apiv1.get("/courses/search/", auth=None)
def search_course(request, keyword: str):

    courses = Course.objects.filter(
        name__icontains=keyword
    )

    data = []

    for c in courses:
        data.append({
            "id": c.id,
            "name": c.name,
            "price": c.price
        })

    return data


# =========================
# API FILTER COURSE PRICE
# =========================
@apiv1.get("/courses/filter/", auth=None)
def filter_course(request, min_price: int):

    courses = Course.objects.filter(
        price__gte=min_price
    )

    data = []

    for c in courses:
        data.append({
            "id": c.id,
            "name": c.name,
            "price": c.price
        })

    return data


# =========================
# API RELASI COURSE + TEACHER
# =========================
@apiv1.get("/course-relasi/", auth=None)
def relasi_course(request):

    courses = Course.objects.select_related('teacher').all()

    data = []

    for c in courses:
        data.append({
            "course": c.name,
            "teacher": c.teacher.username,
            "email": c.teacher.email
        })

    return data


# =========================
# API RELASI COURSE MEMBER
# =========================
@apiv1.get("/course-members/", auth=None)
def course_members(request):

    members = CourseMember.objects.select_related(
        'course_id',
        'user_id'
    ).all()

    data = []

    for m in members:
        data.append({
            "course": m.course_id.name,
            "member": m.user_id.username,
            "role": m.roles
        })

    return data


# =========================
# API CALCULATOR
# =========================
@apiv1.get("/calc/{nil1}/{opr}/{nil2}", auth=None)
def calculator(request, nil1: int, opr: str, nil2: int):

    hasil = 0

    if opr == "tambah":
        hasil = nil1 + nil2

    elif opr == "kurang":
        hasil = nil1 - nil2

    elif opr == "kali":
        hasil = nil1 * nil2

    elif opr == "bagi":
        hasil = nil1 / nil2

    return {
        "nilai_1": nil1,
        "operator": opr,
        "nilai_2": nil2,
        "hasil": hasil
    }


# =========================
# MY COURSES
# =========================
@apiv1.get("/mycourses/", auth=apiAuth)
def my_courses(request):

    user_id = User.objects.get(pk=request.user.id)

    mycourses = CourseMember.objects.filter(
        user_id=user_id
    ).select_related(
        'course_id',
        'user_id'
    )

    data = []

    for m in mycourses:
        data.append({
            "course": m.course_id.name,
            "member": m.user_id.username,
            "role": m.roles
        })

    return data


# =========================
# COURSE ENROLLMENT
# =========================
@apiv1.post("/courses/{course_id}/enroll/", auth=apiAuth)
def enroll_course(request, course_id: int):

    user_id = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, id=course_id)

    enrollment = CourseMember.objects.create(
        user_id=user_id,
        course_id=course
    )

    return {
        "course": enrollment.course_id.name,
        "member": enrollment.user_id.username,
        "role": enrollment.roles
    }


# =========================
# POST COMMENT
# =========================
@apiv1.post("/comments/add/", auth=apiAuth)
def post_comment(request, data: CommentSchema):

    user_id = User.objects.get(pk=request.user.id)

    content = get_object_or_404(
        CourseContent,
        id=data.content_id
    )

    coursemember = CourseMember.objects.filter(
        user_id=user_id,
        course_id=content.course
    )

    if coursemember.exists():

        Comment.objects.create(
            comment=data.comment,
            member_id=coursemember.first(),
            content_id=content
        )

        return {
            "status": "berhasil komentar"
        }

    else:

        return {
            "status": "tidak boleh komentar"
        }
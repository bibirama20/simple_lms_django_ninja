import os
import django
import csv

# SETTING DJANGO
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.contrib.auth.models import User
from lms.models import Course, CourseMember


# =========================
# IMPORT USER
# =========================
print("Importing Users...")

with open('./csv_data/user-data.csv') as csvfile:
    reader = csv.DictReader(csvfile)

    for row in reader:
        username = row.get('username')

        if not User.objects.filter(username=username).exists():
            User.objects.create_user(
                username=username,
                password=row.get('password'),
                email=row.get('email')
            )
            print(f"User {username} dibuat")
        else:
            print(f"User {username} sudah ada (skip)")

print("Users imported ✅")


# =========================
# IMPORT COURSE
# =========================
print("Importing Courses...")

with open('./csv_data/course-data.csv') as csvfile:
    reader = csv.DictReader(csvfile)

    for row in reader:
        name = row.get('name')

        if not Course.objects.filter(name=name).exists():
            teacher_id = row.get('teacher')

            teacher = User.objects.filter(pk=teacher_id).first()

            if not teacher:
                print(f"Teacher ID {teacher_id} tidak ditemukan, skip")
                continue

            Course.objects.create(
                name=name,
                description=row.get('description'),
                price=int(row.get('price', 0)),
                teacher=teacher
            )
            print(f"Course {name} dibuat")
        else:
            print(f"Course {name} sudah ada (skip)")

print("Courses imported ✅")


# =========================
# IMPORT MEMBER
# =========================
print("Importing Course Members...")

with open('./csv_data/member-data.csv') as csvfile:
    reader = csv.DictReader(csvfile)

    for row in reader:
        course = Course.objects.filter(pk=row.get('course_id')).first()
        user = User.objects.filter(pk=row.get('user_id')).first()

        if not course or not user:
            print("Course/User tidak ditemukan, skip")
            continue

        if not CourseMember.objects.filter(course_id=course, user_id=user).exists():
            CourseMember.objects.create(
                course_id=course,
                user_id=user,
                roles=row.get('roles', 'std')
            )
            print(f"Member {user} masuk ke {course}")
        else:
            print(f"Member sudah ada (skip)")

print("Members imported ✅")
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import Course, CourseMember, CourseContent, Enrollment


# =========================
# COURSE
# =========================
class CourseModelTest(TestCase):
    def setUp(self):
        # Buat user
        self.teacher = User.objects.create(username='teacher1')

        # Buat course
        self.course = Course.objects.create(
            name="Pemrograman Django",
            description="Belajar Django",
            price=150000,
            teacher=self.teacher
        )

    def test_course_creation(self):
        # Pastikan course berhasil dibuat
        course = Course.objects.get(name="Pemrograman Django")
        self.assertEqual(course.price, 150000)
        self.assertEqual(course.teacher.username, 'teacher1')
        self.assertEqual(str(course), course.name + " : " + str(course.price))


# =========================
# COURSE MEMBER
# =========================
class CourseMemberModelTest(TestCase):
    def setUp(self):
        # Buat user dan course
        self.teacher = User.objects.create(username='teacher1')
        self.student = User.objects.create(username='student1')
        self.course = Course.objects.create(
            name="Pemrograman Django", teacher=self.teacher
        )

    def test_course_member_creation(self):
        # Buat subscriber untuk course
        member = CourseMember.objects.create(
            course_id=self.course, user_id=self.student, roles='std'
        )

        # Pastikan CourseMember berhasil dibuat
        self.assertEqual(member.user_id.username, 'student1')
        self.assertEqual(member.roles, 'std')


# =========================
# COURSE CONTENT
# =========================
class CourseContentModelTest(TestCase):
    def setUp(self):
        # Buat user dan course
        self.teacher = User.objects.create(username='teacher1')
        self.course = Course.objects.create(
            name="Pemrograman Django", teacher=self.teacher
        )

    def test_course_content_creation(self):
        # Buat konten untuk course
        content = CourseContent.objects.create(
            name="Pengenalan Django",
            course=self.course,
            description="Materi dasar tentang Django"
        )

        # Pastikan CourseContent berhasil dibuat
        self.assertEqual(content.course.name, "Pemrograman Django")
        self.assertEqual(content.name, "Pengenalan Django")
        self.assertEqual(str(content), '[' + content.course.name + '] ' + content.name)


# =========================
# COURSE QUERY
# =========================
class CourseQueryTest(TestCase):
    def setUp(self):
        self.teacher1 = User.objects.create(username='teacher1')
        self.teacher2 = User.objects.create(username='teacher2')
        Course.objects.create(name="Django", teacher=self.teacher1)
        Course.objects.create(name="Flask", teacher=self.teacher2)

    def test_course_retrieval_by_teacher(self):
        # Query kursus yang diajarkan oleh teacher1
        courses = Course.objects.filter(teacher=self.teacher1)

        # Pastikan hanya ada satu course yang ditemukan dan itu milik teacher1
        self.assertEqual(courses.count(), 1)
        self.assertEqual(courses.first().name, "Django")


# =========================
# COURSE VALIDATION
# =========================
class CourseValidationTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create(username='teacher1')

    def test_invalid_price(self):
        # Coba membuat course dengan harga negatif
        course = Course(
            name="Pemrograman Django",
            description="Belajar Django",
            price=-10000,  # Harga tidak valid
            teacher=self.teacher
        )

        # Coba simpan - akan sukses karena belum ada validasi harga
        course.save()

        # Verifikasi bahwa course disimpan dengan harga negatif
        retrieved_course = Course.objects.get(pk=course.pk)
        self.assertEqual(retrieved_course.price, -10000)

    def test_empty_name(self):
        # Coba membuat course tanpa nama
        course = Course(
            name="",  # Nama kosong
            description="Belajar Django",
            price=100000,
            teacher=self.teacher
        )

        # Pastikan ValidationError muncul
        with self.assertRaises(ValidationError):
            course.full_clean()


# =========================
# COURSE FILTERING
# =========================
class CourseFilteringTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create(username='teacher1')
        Course.objects.create(name="Kursus 1", price=100000, teacher=self.teacher)
        Course.objects.create(name="Kursus 2", price=200000, teacher=self.teacher)
        Course.objects.create(name="Kursus 3", price=300000, teacher=self.teacher)

    def test_filter_courses_by_price(self):
        # Filter kursus dengan harga di bawah 200000
        affordable_courses = Course.objects.filter(price__lt=200000)

        # Pastikan hanya ada satu course yang sesuai
        self.assertEqual(affordable_courses.count(), 1)
        self.assertEqual(affordable_courses.first().name, "Kursus 1")


# =========================
# ENROLLMENT
# =========================
class EnrollmentTestCase(TestCase):
    def setUp(self):
        # Membuat data dummy untuk pengujian
        self.teacher = User.objects.create(username='teacher1')
        self.student = User.objects.create(username='student1')
        self.course = Course.objects.create(
            name="Pemrograman Python",
            description="Kursus Python tingkat dasar",
            price=50000,
            teacher=self.teacher
        )

    def test_enrollment_success(self):
        # Simulasi siswa mendaftar kursus
        enrollment = Enrollment.objects.create(
            course=self.course,
            student=self.student,
            status='paid'
        )

        # Pastikan siswa berhasil terdaftar di kursus
        self.assertEqual(enrollment.course.name, "Pemrograman Python")
        self.assertEqual(enrollment.student.username, "student1")
        self.assertEqual(enrollment.status, 'paid')

    def test_duplicate_enrollment(self):
        # Test bahwa siswa tidak bisa mendaftar dua kali ke kursus yang sama
        # Buat enrollment pertama
        Enrollment.objects.create(
            course=self.course,
            student=self.student,
            status='paid'
        )

        # Coba buat enrollment kedua dengan student dan course yang sama
        # Harusnya gagal karena unique_together constraint
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Enrollment.objects.create(
                    course=self.course,
                    student=self.student,
                    status='pending'
                )

    def test_course_full(self):
        # Simulasi kursus penuh (kuota maksimal)
        self.course.max_students = 1
        self.course.save()

        # Daftarkan siswa pertama (harus berhasil)
        enrollment1 = Enrollment.objects.create(
            course=self.course,
            student=self.student,
            status='paid'
        )

        # Pastikan enrollment pertama berhasil
        self.assertEqual(enrollment1.student, self.student)

        # Simulasi siswa kedua mencoba mendaftar
        student2 = User.objects.create(username='student2')

        # Buat objek Enrollment tanpa langsung save
        enrollment2 = Enrollment(
            course=self.course,
            student=student2,
            status='paid'
        )

        # Kuota sudah penuh, sehingga save() harus menolak pendaftaran
        with self.assertRaises(ValidationError):
            enrollment2.save()

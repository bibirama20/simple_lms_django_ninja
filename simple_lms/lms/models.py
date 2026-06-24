import re

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# =========================
# COURSE
# =========================
class Course(models.Model):
    name = models.CharField("nama matkul", max_length=100)
    description = models.TextField("deskripsi", default='-')
    price = models.IntegerField("harga", default=10000)
    image = models.ImageField("gambar", null=True, blank=True)
    max_students = models.PositiveIntegerField("kuota maksimal", null=True, blank=True)

    teacher = models.ForeignKey(
        User,
        verbose_name="pengajar",
        on_delete=models.RESTRICT
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mata Kuliah"
        verbose_name_plural = "Mata Kuliah"

    def __str__(self):
        return f"{self.name} : {self.price}"


# =========================
# COURSE MEMBER
# =========================
ROLE_OPTIONS = [
    ('std', 'Siswa'),
    ('ast', 'Asisten')
]

class CourseMember(models.Model):
    course_id = models.ForeignKey(
        Course,
        verbose_name="matkul",
        on_delete=models.RESTRICT
    )
    user_id = models.ForeignKey(
        User,
        verbose_name="siswa",
        on_delete=models.RESTRICT
    )

    roles = models.CharField(
        "peran",
        max_length=3,
        choices=ROLE_OPTIONS,
        default='std'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Subscriber Matkul"
        verbose_name_plural = "Subscriber Matkul"

    def __str__(self):
        return f"{self.course_id} : {self.user_id}"


# =========================
# COURSE CONTENT
# =========================
class CourseContent(models.Model):
    name = models.CharField("judul konten", max_length=200)
    description = models.TextField("deskripsi", default='-')

    video_url = models.URLField("URL Video", null=True, blank=True)  # ✅ lebih tepat
    file_attachment = models.FileField("File", upload_to='materi/', null=True, blank=True)  # ✅ tambah upload path

    course = models.ForeignKey(   # ✅ GANTI course_id → course
        Course,
        verbose_name="matkul",
        on_delete=models.RESTRICT,
        related_name='contents'   # ✅ penting untuk relasi balik
    )

    parent = models.ForeignKey(   # ✅ GANTI parent_id → parent
        'self',
        verbose_name="induk",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name='children'   # ✅ untuk nested konten
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Konten Matkul"
        verbose_name_plural = "Konten Matkul"

    def __str__(self):
        return f"[{self.course.name}] {self.name}"  # ✅ lebih clean

    @property
    def embed_url(self):
        # YouTube hanya bisa di-embed lewat format /embed/<id>, bukan link watch/share biasa
        if not self.video_url:
            return None

        match = re.search(
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]+)',
            self.video_url
        )

        if match:
            return f"https://www.youtube.com/embed/{match.group(1)}"

        return self.video_url

    @property
    def watch_url(self):
        # Link biasa untuk dibuka langsung di tab baru (bukan di dalam iframe).
        # video_url tersimpan dalam format /embed/<id>, yang akan error 153
        # kalau dibuka langsung sebagai halaman, bukan di dalam iframe.
        if not self.video_url:
            return None

        match = re.search(
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]+)',
            self.video_url
        )

        if match:
            return f"https://www.youtube.com/watch?v={match.group(1)}"

        return self.video_url


# =========================
# COMMENT
# =========================
class Comment(models.Model):
    content_id = models.ForeignKey(
        CourseContent,
        verbose_name="konten",
        on_delete=models.CASCADE,
        related_name='comments',
        null=True,
        blank=True,
    )

    title = models.CharField(
        "judul topik",
        max_length=200,
        blank=True,
        default=''
    )

    member_id = models.ForeignKey(
        CourseMember,
        verbose_name="pengguna",
        on_delete=models.CASCADE
    )

    comment = models.TextField("komentar")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.comment


# =========================
# ENROLLMENT
# =========================
ENROLLMENT_STATUS = [
    ('pending', 'Menunggu Pembayaran'),
    ('paid', 'Dibayar'),
]

class Enrollment(models.Model):
    course = models.ForeignKey(
        Course,
        verbose_name="matkul",
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    student = models.ForeignKey(
        User,
        verbose_name="siswa",
        on_delete=models.CASCADE
    )

    status = models.CharField(
        "status",
        max_length=10,
        choices=ENROLLMENT_STATUS,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pendaftaran Kursus"
        verbose_name_plural = "Pendaftaran Kursus"
        unique_together = ('course', 'student')

    def __str__(self):
        return f"{self.student.username} - {self.course.name} ({self.status})"

    def save(self, *args, **kwargs):
        if self.pk is None and self.status == 'paid' and self.course.max_students is not None:
            paid_count = Enrollment.objects.filter(
                course=self.course, status='paid'
            ).count()

            if paid_count >= self.course.max_students:
                raise ValidationError("Kuota kursus sudah penuh")

        super().save(*args, **kwargs)
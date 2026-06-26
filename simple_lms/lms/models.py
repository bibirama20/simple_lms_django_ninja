import re

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# =========================
# COURSE
# =========================
COURSE_CATEGORIES = [
    ('design', 'Design'),
    ('development', 'Development'),
    ('business', 'Business'),
    ('marketing', 'Marketing'),
    ('data_science', 'Data Science'),
    ('photography', 'Photography'),
]

class Course(models.Model):
    name = models.CharField("nama matkul", max_length=100)
    description = models.TextField("deskripsi", default='-')
    price = models.IntegerField("harga", default=10000)
    image = models.ImageField("gambar", null=True, blank=True)
    max_students = models.PositiveIntegerField("kuota maksimal", null=True, blank=True)
    category = models.CharField(
        "kategori",
        max_length=20,
        choices=COURSE_CATEGORIES,
        default='development'
    )

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
        unique_together = ('course_id', 'user_id')

    def __str__(self):
        return f"{self.course_id} : {self.user_id}"


# =========================
# COURSE CONTENT
# =========================
class CourseContent(models.Model):
    name = models.CharField("judul konten", max_length=200)
    description = models.TextField("deskripsi", default='-')

    video_url = models.URLField("URL Video", null=True, blank=True)  # ✅ lebih tepat
    video_file = models.FileField("Video Lokal", upload_to='videos/', null=True, blank=True)
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
    def has_video(self):
        return bool(self.video_file) or bool(self.video_url)

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

    # Diisi hanya untuk ulasan course (beda dari diskusi per-konten di atas)
    course = models.ForeignKey(
        Course,
        verbose_name="matkul (ulasan)",
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,
        blank=True,
    )

    rating = models.PositiveSmallIntegerField(
        "rating",
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
# COMMENT REPLY (balasan admin/pengajar atas pertanyaan diskusi siswa)
# =========================
class CommentReply(models.Model):
    comment = models.ForeignKey(
        Comment,
        verbose_name="komentar",
        on_delete=models.CASCADE,
        related_name='replies'
    )
    admin = models.ForeignKey(
        User,
        verbose_name="dibalas oleh",
        on_delete=models.CASCADE,
        related_name='comment_replies'
    )
    text = models.TextField("balasan")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Balasan Diskusi"
        verbose_name_plural = "Balasan Diskusi"
        ordering = ['created_at']

    def __str__(self):
        return f"Balasan {self.admin.username} untuk komentar #{self.comment_id}"


# =========================
# CONTENT PROGRESS
# =========================
class ContentProgress(models.Model):
    member = models.ForeignKey(
        CourseMember,
        verbose_name="siswa",
        on_delete=models.CASCADE,
        related_name='progress'
    )
    content = models.ForeignKey(
        CourseContent,
        verbose_name="konten",
        on_delete=models.CASCADE,
        related_name='progress_entries'
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Progress Materi"
        verbose_name_plural = "Progress Materi"
        unique_together = ('member', 'content')

    def __str__(self):
        return f"{self.member} selesai {self.content}"


# =========================
# NOTE (catatan pribadi siswa per materi)
# =========================
class Note(models.Model):
    member = models.ForeignKey(
        CourseMember,
        verbose_name="siswa",
        on_delete=models.CASCADE,
        related_name='notes'
    )
    content = models.ForeignKey(
        CourseContent,
        verbose_name="konten",
        on_delete=models.CASCADE,
        related_name='notes'
    )
    text = models.TextField("catatan")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Catatan Pribadi"
        verbose_name_plural = "Catatan Pribadi"
        unique_together = ('member', 'content')

    def __str__(self):
        return f"Catatan {self.member} di {self.content}"


# =========================
# CERTIFICATE (sertifikat penyelesaian course)
# =========================
class Certificate(models.Model):
    member = models.OneToOneField(
        CourseMember,
        verbose_name="keanggotaan",
        on_delete=models.CASCADE,
        related_name='certificate'
    )
    code = models.CharField("kode sertifikat", max_length=24, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sertifikat"
        verbose_name_plural = "Sertifikat"

    def __str__(self):
        return f"Sertifikat {self.code} — {self.member}"


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
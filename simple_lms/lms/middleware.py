import time

from django.conf import settings
from django.contrib.sessions.backends.base import UpdateError
from django.contrib.sessions.exceptions import SessionInterrupted
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date

ADMIN_SESSION_COOKIE_NAME = 'admin_sessionid'


class DualCookieSessionMiddleware(SessionMiddleware):
    """Pakai cookie sesi terpisah untuk /admin/ ('admin_sessionid') dari
    cookie sesi siswa/publik ('sessionid' bawaan Django). Tanpa ini, login
    sebagai admin di /admin/ akan menimpa sesi siswa yang sedang login di
    tab/browser yang sama karena keduanya berbagi satu cookie 'sessionid'.
    Dengan cookie terpisah, dua sesi login bisa hidup berdampingan.

    Subclass SessionMiddleware (bukan middleware baru dari nol) supaya lolos
    pengecekan admin.E410 yang mewajibkan SessionMiddleware (atau turunannya)
    ada di MIDDLEWARE."""

    def _cookie_name(self, request):
        return ADMIN_SESSION_COOKIE_NAME if request.path.startswith('/admin/') else settings.SESSION_COOKIE_NAME

    def process_request(self, request):
        cookie_name = self._cookie_name(request)
        session_key = request.COOKIES.get(cookie_name)
        request.session = self.SessionStore(session_key)

    def process_response(self, request, response):
        cookie_name = self._cookie_name(request)

        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response

        if cookie_name in request.COOKIES and empty:
            response.delete_cookie(
                cookie_name,
                path=settings.SESSION_COOKIE_PATH,
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
            patch_vary_headers(response, ('Cookie',))
        else:
            if accessed:
                patch_vary_headers(response, ('Cookie',))
            if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
                if request.session.get_expire_at_browser_close():
                    max_age = None
                    expires = None
                else:
                    max_age = request.session.get_expiry_age()
                    expires = http_date(time.time() + max_age)

                if response.status_code < 500:
                    try:
                        request.session.save()
                    except UpdateError:
                        raise SessionInterrupted(
                            "The request's session was deleted before the "
                            "request completed. The user may have logged "
                            "out in a concurrent request, for example."
                        )
                    response.set_cookie(
                        cookie_name,
                        request.session.session_key,
                        max_age=max_age,
                        expires=expires,
                        domain=settings.SESSION_COOKIE_DOMAIN,
                        path=settings.SESSION_COOKIE_PATH,
                        secure=settings.SESSION_COOKIE_SECURE or None,
                        httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                        samesite=settings.SESSION_COOKIE_SAMESITE,
                    )

        return response


class NoCacheForAuthenticatedMiddleware:
    """Cegah browser menyimpan halaman yang dirender saat login di cache/
    back-forward cache, supaya tombol Back setelah logout tidak menampilkan
    halaman lama tanpa mengecek ulang sesi ke server."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if getattr(request, 'user', None) and request.user.is_authenticated:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response

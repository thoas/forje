import socket
import re

from collections import OrderedDict
from threading import Lock, local

from django.conf import settings
from django.utils.encoding import DjangoUnicodeDecodeError
from django.utils.html import strip_spaces_between_tags as minify_html
from django.core.cache.backends.locmem import LocMemCache
from django.core.cache.backends.base import BaseCache

_thread_locals = local()


class RequestCache(LocMemCache):
    def __init__(self):
        # We explicitly do not call super() here, because while we want BaseCache.__init__() to run, we *don't*
        # want LocMemCache.__init__() to run, because that would store our caches in its globals.
        BaseCache.__init__(self, params={})

        self._cache = OrderedDict()
        self._expire_info = {}
        self._lock = Lock()


def set_current_request(request):
    return setattr(_thread_locals, "_request", request)


def get_current_request():
    return getattr(_thread_locals, "_request", None)


class RequestCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.cache = RequestCache()

        set_current_request(request)

        response = self.get_response(request)

        return response


class MinifyHTMLMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if (
            response.has_header("Content-Type")
            and "text/html" in response["Content-Type"]
        ):
            try:
                match = re.search(r"charset=([^;\s]+)", response["Content-Type"])
                encoding = match.group(1) if match else "utf-8"

                response.content = str(
                    minify_html(response.content.strip().decode(encoding))
                )
                response["Content-Length"] = str(len(response.content))
            except DjangoUnicodeDecodeError:
                pass

        return response


TYPES = (socket.AF_INET, socket.AF_INET6)


def is_valid(ip):
    for af in TYPES:
        try:
            socket.inet_pton(af, ip)
            return True
        except socket.error:
            pass
    return False


class SetRemoteAddrFromForwardedFor(object):
    """
    Replaces the Django 1.1 middleware to replace the remote IP with
    the value of the X-Forwarded-For header for use behind reverse proxy
    servers, like load balancers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ips = []

        if "HTTP_X_FORWARDED_FOR" in request.META:
            xff = [i.strip() for i in request.META["HTTP_X_FORWARDED_FOR"].split(",")]
            ips = [ip for ip in xff if is_valid(ip)]
        else:
            return self.get_response(request)

        ips.append(request.META["REMOTE_ADDR"])

        known = getattr(settings, "KNOWN_PROXIES", [])
        ips.reverse()
        for ip in ips:
            request.META["REMOTE_ADDR"] = ip
            if ip not in known:
                break

        return self.get_response(request)

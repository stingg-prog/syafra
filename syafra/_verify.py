#!/usr/bin/env python
"""Verify all critical pages load without errors."""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syafra.settings')
os.environ['DEBUG'] = 'true'
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth.models import AnonymousUser

factory = RequestFactory()

pages = [
    ('Homepage', 'products:home', {}),
    ('Shop', 'products:shop', {}),
    ('Contact', 'products:contact', {}),
    ('Track Order', 'products:track_order', {}),
    ('Login', 'accounts:login', {}),
    ('Register', 'accounts:register', {}),
    ('Password Reset', 'accounts:password_reset', {}),
]

results = []

for name, url_name, kwargs in pages:
    try:
        from django.urls import reverse
        url = reverse(url_name, kwargs=kwargs) if kwargs else reverse(url_name)
        request = factory.get(url)
        request.user = AnonymousUser()

        from django.urls import resolve
        match = resolve(url)
        view_func = match.func

        response = view_func(request, **match.kwargs)
        status = response.status_code
        if status == 200:
            results.append((name, url, status, True))
        else:
            results.append((name, url, status, False))
    except Exception as e:
        results.append((name, url_name, 0, False))
        results[-1] = (name, url_name, str(e)[:80], False)

print("=== Page Verification ===")
for name, url, info, ok in results:
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {name} ({url}) -> {info}")

# Admin check
try:
    c = Client()
    resp = c.get('/admin/login/')
    admin_ok = resp.status_code in (200, 302)
    print(f"  [{'OK' if admin_ok else 'FAIL'}] Admin login page -> {resp.status_code}")
except Exception as e:
    print(f"  [FAIL] Admin -> {str(e)[:80]}")

print("\n=== VERIFICATION COMPLETE ===")

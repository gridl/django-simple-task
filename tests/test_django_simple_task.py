import asyncio
import os
from unittest import mock

import pytest
from async_asgi_testclient import TestClient
from django.http import HttpResponse
from django.urls.conf import path

from django_simple_task import defer

os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"


@pytest.fixture
async def get_app():
    async def _get_app(patterns):
        from . import urls, app

        urls.urlpatterns.clear()
        urls.urlpatterns.extend(patterns)
        return app.application

    return _get_app


@pytest.mark.asyncio
async def test_sanity_check(get_app):
    def view(requests):
        return HttpResponse("Foo")

    app = await get_app([path("", view)])
    async with TestClient(app) as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.text == "Foo"


@pytest.mark.asyncio
async def test_should_call_task(get_app):
    task = mock.MagicMock()

    def view(requests):
        defer(task)
        return HttpResponse("Foo1")

    app = await get_app([path("", view)])
    async with TestClient(app) as client:
        task.assert_not_called()
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.text == "Foo1"
    task.assert_called_once()


@pytest.mark.asyncio
async def test_should_call_async_task(get_app):
    cb = mock.MagicMock()

    async def task():
        await asyncio.sleep(1)
        cb()

    def view(requests):
        defer(task)
        defer(task)
        defer(task)
        defer(task)
        return HttpResponse("Foo")

    app = await get_app([path("", view)])
    async with TestClient(app) as client:
        cb.assert_not_called()
        resp = await client.get("/")
        assert resp.text == "Foo"
        cb.assert_not_called()
    assert cb.call_count == 4

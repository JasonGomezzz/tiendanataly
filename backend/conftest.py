import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from tests import factories


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Crea los grupos Administradora y Staff una sola vez para toda la sesión de tests."""
    with django_db_blocker.unblock():
        call_command("setup_roles")


@pytest.fixture(autouse=True)
def _clear_cache():
    from django.core.cache import cache

    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def admin_role(db):
    return factories.make_user("tia", groups=["Administradora"], staff=True)


@pytest.fixture
def staff_role(db):
    return factories.make_user("empleada", groups=["Staff"], staff=True)


@pytest.fixture
def superuser(db):
    return factories.make_user("dev", staff=True, superuser=True)


@pytest.fixture
def customer_user(db):
    user = factories.make_user("clienta1")
    factories.make_customer(user)
    return user


@pytest.fixture
def other_customer_user(db):
    user = factories.make_user("clienta2")
    factories.make_customer(user, nombre="Otra Clienta")
    return user

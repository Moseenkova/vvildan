from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request as StarletteRequest

from src.config import get_settings
from src.database import (
    AdminUser,
    City,
    CityName,
    Country,
    CountryName,
    CustomerTgTopic,
    Match,
    RefreshToken,
    Request,
    User,
    async_session_maker,
    engine,
)


class AdminAuthentication(AuthenticationBackend):
    async def login(self, request: StarletteRequest) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            return False

        async with async_session_maker() as session:
            user = await session.scalar(
                select(AdminUser).where(AdminUser.username == username)
            )

        if user is None or not user.is_superuser or not user.verify_password(password):
            return False

        request.session.update({"admin_user_id": user.id})
        return True

    async def logout(self, request: StarletteRequest) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: StarletteRequest) -> bool:
        user_id = request.session.get("admin_user_id")
        if not isinstance(user_id, int):
            return False

        async with async_session_maker() as session:
            user = await session.get(AdminUser, user_id)
        return user is not None and user.is_superuser


class AdminUserView(ModelView, model=AdminUser):
    column_exclude_list = [AdminUser.password_hash]
    form_excluded_columns = [AdminUser.password_hash]
    can_create = False


class UserView(ModelView, model=User):
    pass


class RequestView(ModelView, model=Request):
    pass


class MatchView(ModelView, model=Match):
    pass


class CountryView(ModelView, model=Country):
    pass


class CityView(ModelView, model=City):
    pass


class CountryNameView(ModelView, model=CountryName):
    pass


class CityNameView(ModelView, model=CityName):
    pass


class RefreshTokenView(ModelView, model=RefreshToken):
    pass


class CustomerTgTopicView(ModelView, model=CustomerTgTopic):
    pass


def setup_admin(app) -> Admin:
    admin = Admin(
        app,
        engine,
        authentication_backend=AdminAuthentication(get_settings().SECRET_KEY),
    )
    for view in (
        AdminUserView,
        UserView,
        RequestView,
        MatchView,
        CountryView,
        CityView,
        CountryNameView,
        CityNameView,
        RefreshTokenView,
        CustomerTgTopicView,
    ):
        admin.add_view(view)
    return admin

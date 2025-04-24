from dependency_injector import containers, providers

from app.core.config import settings
# from app.db.session import session


class AppContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    config.from_dict(settings.model_dump())

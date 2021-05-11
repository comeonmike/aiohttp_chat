import asyncio

import aiohttp_debugtoolbar
import aiohttp_jinja2
import aioredis
import jinja2
import peewee_async
from aiohttp import web
from aiohttp_session import session_middleware
from aiohttp_session.redis_storage import RedisStorage

import settings
from helpers.middlewares import request_user_middleware
from helpers.models import database
from helpers.template_tags import tags
from settings import logger


async def create_app():
    """ Prepare application """
    redis_pool = await aioredis.create_pool(settings.REDIS_CON)
    middlewares = [session_middleware(RedisStorage(redis_pool)), request_user_middleware]
    if settings.DEBUG:
        middlewares.append(aiohttp_debugtoolbar.middleware)
    # init application
    app = web.Application(middlewares=middlewares)
    app.redis_pool = redis_pool
    app.ws_list = {}
    jinja_env = aiohttp_jinja2.setup(
        app, loader=jinja2.FileSystemLoader(settings.TEMPLATE_DIR),
        context_processors=[aiohttp_jinja2.request_processor], )
    jinja_env.globals.update(tags)
    if settings.DEBUG:
        aiohttp_debugtoolbar.setup(app, intercept_redirects=False)
    # db conn
    database.init(**settings.DATABASE)
    app.database = database
    app.database.set_allow_sync(False)
    app.objects = peewee_async.Manager(app.database)
    # make routes
    from urls import routes
    for route in routes:
        app.router.add_route(**route)
    app.router.add_static('/static', settings.STATIC_DIR, name='static')

    app.logger = logger
    return app


if __name__ == '__main__':
    web.run_app(create_app(), host=settings.HOST, port=settings.PORT)

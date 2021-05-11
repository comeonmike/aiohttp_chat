import re
from time import time

import aiohttp_jinja2
from aiohttp import web

from accounts.models import User
from helpers.tools import redirect, add_message
from helpers.decorators import anonymous_required, login_required


class LogIn(web.View):

    """ Simple Login user by username """

    template_name = 'accounts/login.html'

    @anonymous_required
    @aiohttp_jinja2.template(template_name)
    async def get(self):
        return {}

    @anonymous_required
    async def post(self):
        """ Check username and login """
        username = await self.is_valid()
        if not username:
            redirect(self.request, 'login')
        try:
            user = await self.request.app.objects.get(User, User.username ** username)
            await self.login_user(user)
        except User.DoesNotExist:
            add_message(self.request, 'danger', f'User {username} not found')
        redirect(self.request, 'login')

    async def login_user(self, user):
        """ Put user to session and redirect to Index """
        self.request.session['user'] = str(user.id)
        self.request.session['time'] = time()
        add_message(self.request, 'info', f'Hello {user}!')
        redirect(self.request, 'index')

    async def is_valid(self):
        """ Get username from post data, and check is correct """
        data = await self.request.post()
        username = data.get('username', '').lower()
        if not re.match(r'^[a-z]\w{0,9}$', username):
            add_message(
                self.request, 'warning', 'Username should be alphanumeric, with length [1 .. 10], startswith letter!')
            return False
        return username


class LogOut(web.View):

    """ Remove current user from session """

    @login_required
    async def get(self):
        self.request.session.pop('user')
        add_message(self.request, 'info', 'You are logged out')
        redirect(self.request, 'index')


class Register(LogIn):

    """ Create new user in db """

    template_name = 'accounts/register.html'

    @anonymous_required
    @aiohttp_jinja2.template(template_name)
    async def get(self):
        return {}

    @anonymous_required
    async def post(self):
        """ Check is username unique and create new User """
        username = await self.is_valid()
        if not username:
            redirect(self.request, 'register')
        if await self.request.app.objects.count(User.select().where(User.username ** username)):
            add_message(self.request, 'danger', f'{username} already exists')
            redirect(self.request, 'register')
        user = await self.request.app.objects.create(User, username=username)
        await self.login_user(user)

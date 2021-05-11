import re
import aiohttp_jinja2

from textwrap import dedent
from aiohttp import web, WSMsgType

from chat.models import Room, Message
from helpers.decorators import login_required
from helpers.tools import redirect, add_message, get_object_or_404


class CreateRoom(web.View):

    """ Create new chat room """

    @login_required
    @aiohttp_jinja2.template('chat/rooms.html')
    async def get(self):
        return {}
        # return {'chat_rooms': await Room.all_rooms(self.request.app.objects)}

    @login_required
    async def post(self):
        """ Check is roomname unique and create new User """
        roomname = await self.is_valid()
        if not roomname:
            redirect(self.request, 'create_room')
        if await self.request.app.objects.count(Room.select().where(Room.name ** roomname)):
            add_message(self.request, 'danger', f'Room with {roomname} already exists.')
            redirect(self.request, 'create_room')
        room = await self.request.app.objects.create(Room, name=roomname)
        redirect(self.request, 'room', parts=dict(slug=room.name))

    async def is_valid(self):
        """ Get roomname from post data, and check is correct """
        data = await self.request.post()
        roomname = data.get('roomname', '').lower()
        if not re.match(r'^[a-z]\w{0,31}$', roomname):
            add_message(self.request, 'warning', (
                'Room name should be alphanumeric, with length [1 .. 32], startswith letter!'))
            return False
        return roomname


class ChatRoom(web.View):

    """ Get room by slug display messages in this Room """

    @login_required
    @aiohttp_jinja2.template('chat/chat.html')
    async def get(self):
        room = await get_object_or_404(self.request, Room, name=self.request.match_info['slug'].lower())
        return {
            'room': room, 'chat_rooms': await Room.all_rooms(self.request.app.objects),
            'room_messages': await room.all_messages(self.request.app.objects)}


class WebSocket(web.View):

    """ Process WS connections """

    async def get(self):
        self.room = await get_object_or_404(self.request, Room, name=self.request.match_info['slug'].lower())
        user = self.request.user
        app = self.request.app

        app.logger.debug('Prepare WS connection')
        ws = web.WebSocketResponse()
        await ws.prepare(self.request)
        if self.room.id not in app.ws_list:
            app.ws_list[self.room.id] = {}
        message = await app.objects.create(
            Message, room=self.room, user=None, text=f'@{user.username} join chat room')
        app.ws_list[self.room.id][user.username] = ws
        await self.broadcast(message)
        async for msg in ws:
            if msg.type == WSMsgType.text:
                if msg.data == 'close':
                    await ws.close()
                else:
                    text = msg.data.strip()
                    if text.startswith('/'):
                        ans = await self.command(text)
                        if ans is not None:
                            await ws.send_json(ans)
                    else:
                        message = await app.objects.create(Message, room=self.room, user=user, text=text)
                        await self.broadcast(message)
            elif msg.type == WSMsgType.error:
                app.logger.debug(f'Connection closed with exception {ws.exception()}')
        await self.disconnect(user.username, ws)
        return ws

    async def command(self, cmd):
        """ Run chat command """
        app = self.request.app
        app.logger.debug(f'Chat command {cmd}')
        if cmd.startswith('/kill'):
            # unconnect user from room
            try:
                target = cmd.split(' ')[1]
                peer = app.ws_list[self.room.id][target]
                await self.disconnect(target, peer, silent=True)
                app.logger.debug(f'User {target} killed')
            except KeyError:
                pass
        elif cmd == '/clear':
            # drop all room messages
            count = await app.objects.execute(Message.delete().where(Message.room == self.room))
            app.logger.debug(f'Removed {count} messages')
            for peer in app.ws_list[self.room.id].values():
                peer.send_json({'cmd': 'empty'})
        elif cmd == '/help':
            return {'text': dedent('''\
                - /help - display this msg
                - /kill {username} - remove user from room
                - /clear - empty all messages in room
                ''')}
        else:
            return {'text': 'wrong cmd {cmd}'}

    async def broadcast(self, message):
        """ Send messages to all in this room """
        for peer in self.request.app.ws_list[self.room.id].values():
            await peer.send_json(message.as_dict())

    async def disconnect(self, username, socket, silent=False):
        """ Close connection and notify broadcast """
        app = self.request.app
        app.ws_list.pop(username, None)
        if not socket.closed:
            await socket.close()
        if silent:
            return
        # left chat
        message = await app.objects.create(
            Message, room=self.room, user=None, text=f'@{username} left chat room')
        await self.broadcast(message)

from chat.models import Room, Message
from accounts.models import User
from helpers.models import database
import settings


database.init(**settings.DATABASE)
database.connect()
database.create_tables([User, Room, Message])

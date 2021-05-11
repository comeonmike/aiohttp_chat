from index.urls import routes as index_routes
from accounts.urls import routes as accounts_routes
from chat.urls import routes as chat_routes


routes = (
    * index_routes,
    * accounts_routes,
    * chat_routes,
)

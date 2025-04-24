from app.infrastructures.websocket.implements import ConnectionManager, WebSocketEventHandler, RoomManager
from app.infrastructures.websocket.services import WebSocketService

connection_manager = ConnectionManager()
event_handler = WebSocketEventHandler()
room_manager = RoomManager(connection_manager)
websocket_service = WebSocketService(connection_manager, event_handler, room_manager)


def get_connection_manager():
    return connection_manager


def get_event_handler():
    return event_handler


def get_room_manager():
    return room_manager


def get_websocket_service():
    return websocket_service

import socket
import threading
from ui import ChatUI
import random
from collections import OrderedDict
from dataclasses import dataclass

from common import receive_packet, send_message, PacketType

PORT = 1234
HEADER_LENGTH = 2


@dataclass
class Message:
    username: str
    content: str
    # TODO unread, number of unread in ui
    # read: bool


class Client:
    def __init__(self):
        # povezi se na streznik
        print("[system] connecting to chat server ...")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("localhost", PORT))
        print("[system] connected!")

        # zazeni message_receiver funkcijo v loceni niti
        thread = threading.Thread(target=self.packet_receiver)
        thread.daemon = True
        thread.start()

        self.ui = ChatUI(self)
        self.rooms = OrderedDict[str, list[Message]]({"public": []})
        self.username = ""

    def start(self):
        self.ui.start()

    # message_receiver funkcija tece v loceni niti
    def packet_receiver(self):
        while True:
            packet = receive_packet(self.sock)
            type_ = packet["type"]
            if type_ == PacketType.user_list_init:
                users = packet["users"]
                self.init_rooms(users)
            elif type_ == PacketType.user_left:
                user = packet["user"]
                self.handle_user_disconnect(user)
            elif type_ == PacketType.message:
                content = packet["content"]
                sender = packet["sender"]
                receiver = packet["receiver"]
                room = "public" if receiver == "public" else sender
                self.add_new_message(sender, content, room)
            elif type_ == PacketType.error:
                # TODO: error screen
                print("There was an error")

    def init_user(self, name: str):
        self.username = name
        send_message(self.sock, {"type": PacketType.init, "sender": name})
        print(f"[system] assigned username {name}")

    def init_rooms(self, users: list[str]):
        for room in users:
            self.rooms[room] = []
        self.ui.redraw()

    def handle_user_disconnect(self, user: str):
        self.ui.handle_user_disconnect(user)
        if user in self.rooms:
            del self.rooms[user]
        self.ui.redraw()

    def add_new_message(self, sender: str, content: str, room: str):
        msg = Message(username=sender, content=content)
        self.rooms[room].append(msg)
        self.ui.redraw()

    def send_message(self, content: str, receiver: str):
        message = {
            "type": PacketType.message,
            "content": content,
            "receiver": receiver,
            "sender": self.username,
        }
        self.add_new_message(self.username, content, receiver)
        send_message(self.sock, message)


if __name__ == "__main__":
    client = Client()
    client.start()

import socket
import threading
from ui import ChatUI
from collections import OrderedDict
from dataclasses import dataclass
import argparse

from common import (
    get_common_name,
    receive_packet,
    send_message,
    PacketType,
    setup_SSL_context,
)

PORT = 1234
SERVER_CERTFILE = "server.pem"


@dataclass
class Message:
    username: str
    content: str
    # TODO unread, number of unread in ui
    # read: bool


class Client:
    def __init__(self, certfile: str, keyfile: str):
        print("[system] connecting to chat server ...")

        ssl_ctx = setup_SSL_context(certfile, keyfile, SERVER_CERTFILE)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock = ssl_ctx.wrap_socket(sock)
        self.sock.connect(("localhost", PORT))

        print("[system] connected!")

        # zazeni message_receiver funkcijo v loceni niti
        thread = threading.Thread(target=self.packet_receiver)
        thread.daemon = True
        thread.start()

        self.ui = ChatUI(self)
        self.rooms = OrderedDict[str, list[Message]]({"public": []})
        self.username = get_common_name(certfile)

    def start(self):
        self.ui.start()

    # message_receiver funkcija tece v loceni niti
    def packet_receiver(self):
        while True:
            packet = receive_packet(self.sock)
            if not packet:
                continue

            type_ = packet["type"]
            if type_ == PacketType.user_list_init:
                users = packet["users"]
                self.init_rooms(users)
            elif type_ == PacketType.user_joined:
                user = packet["user"]
                self.init_rooms([user])
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
    parser = argparse.ArgumentParser(description="RK chat client application")
    parser.add_argument(
        "--certfile", type=str, required=True, help="Path to the certificate file"
    )
    parser.add_argument(
        "--keyfile", type=str, required=True, help="Path to the private key file"
    )
    args = parser.parse_args()
    certfile = args.certfile
    keyfile = args.keyfile
    client = Client(certfile, keyfile)
    client.start()

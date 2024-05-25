import socket
import ssl
import threading
from common import (
    receive_packet,
    send_message,
    PacketType,
    get_cert_common_name,
    setup_SSL_context,
)

PORT = 1234
CLIENT_CERTS_FILE = "clients.pem"
SERVER_CERT_FILE = "server.pem"
SERVER_KEY_FILE = "serverkey.pem"

# TODO: refactor this into a class to prevent this bulshit with globals


def handle_message(packet: dict[str, str | int], sock: ssl.SSLSocket):
    global clients
    sender = packet["sender"]
    receiver = packet["receiver"]
    content = packet["content"]
    message = {
        "type": PacketType.message,
        "sender": sender,
        "content": content,
        "receiver": receiver,
    }
    if receiver == "public":
        for name, client in clients.items():
            if name == sender:
                continue
            send_message(client, message)
    else:
        if receiver not in clients:
            send_message(sock, {"type": PacketType.error})
            return
        send_message(clients[receiver], message)


# funkcija za komunikacijo z odjemalcem (tece v loceni niti za vsakega odjemalca)
def client_thread(client_sock: ssl.SSLSocket, client_addr: str):
    global clients

    print("[system] connected with " + client_addr[0] + ":" + str(client_addr[1]))
    username = get_cert_common_name(client_sock)
    init_client(client_sock, username)
    print("clients", clients.keys())
    try:
        while True:  # neskoncna zanka
            packet = receive_packet(client_sock)
            if not packet:  # ce obstaja sporocilo
                continue
            type_ = packet["type"]

            print(
                "[packet] [" + client_addr[0] + ":" + str(client_addr[1]) + "] : ",
                packet,
            )

            if type_ == PacketType.message:
                handle_message(packet, client_sock)
            else:
                # TODO: this is an error
                pass
    except:
        # tule bi lahko bolj elegantno reagirali, npr. na posamezne izjeme. Trenutno kar pozremo izjemo
        pass  # prisli smo iz neskoncne zanke
    teardown_client(client_sock, username)


def init_client(client_sock: ssl.SSLSocket, username: str):
    global clients
    for _, client in clients.items():
        send_message(client, {"type": PacketType.user_joined, "user": username})
    all_users = list(clients.keys())
    with clients_lock:
        clients[username] = client_sock
    print("[system] we now have " + str(len(clients)) + " clients")
    message = {"type": PacketType.user_list_init, "users": all_users}
    send_message(client_sock, message)


def teardown_client(client_sock: ssl.SSLSocket, username: str):
    global clients
    with clients_lock:
        if username and username in clients:
            del clients[username]
            for _, client in clients.items():
                send_message(client, {"type": PacketType.user_left, "user": username})
            print("[system] we now have " + str(len(clients)) + " clients")
    client_sock.close()


# kreiraj socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("localhost", PORT))
server_socket.listen(1)

ssl_ctx = setup_SSL_context(SERVER_CERT_FILE, SERVER_KEY_FILE, CLIENT_CERTS_FILE)

# cakaj na nove odjemalce
print("[system] listening ...")
clients = {}
clients_lock = threading.Lock()

while True:
    try:
        # pocakaj na novo povezavo - blokirajoc klic
        client_sock, client_addr = server_socket.accept()
        client_sock = ssl_ctx.wrap_socket(client_sock, server_side=True)

        thread = threading.Thread(target=client_thread, args=(client_sock, client_addr))
        thread.daemon = True
        thread.start()

    except KeyboardInterrupt:
        break

print("[system] closing server socket ...")
server_socket.close()

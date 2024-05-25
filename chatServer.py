import signal

signal.signal(signal.SIGINT, signal.SIG_DFL)
import socket
import threading
from common import receive_packet, send_message, PacketType, get_username_from_conn

PORT = 1234


def handle_message(packet, sock):
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
def client_thread(client_sock, client_addr):
    global clients

    print("[system] connected with " + client_addr[0] + ":" + str(client_addr[1]))
    username = get_username_from_conn(client_sock)
    try:

        while True:  # neskoncna zanka
            packet = receive_packet(client_sock)
            type_ = packet["type"]
            if not packet:  # ce obstaja sporocilo
                break

            print(
                "[packet] [" + client_addr[0] + ":" + str(client_addr[1]) + "] : ",
                packet,
            )

            sender = packet["sender"]
            if type_ == PacketType.init:
                for name, client in clients.items():
                    # TODO: add PacketType.user_joined, and change type
                    send_message(
                        client, {"type": PacketType.user_list_init, "users": [sender]}
                    )
                all_users = list(clients.keys())
                with clients_lock:
                    username = sender
                    clients[sender] = client_sock
                print("[system] we now have " + str(len(clients)) + " clients")
                message = {"type": PacketType.user_list_init, "users": all_users}
                send_message(client_sock, message)
            elif type_ == PacketType.message:
                handle_message(packet, client_sock)
    except:
        # tule bi lahko bolj elegantno reagirali, npr. na posamezne izjeme. Trenutno kar pozremo izjemo
        pass

    # prisli smo iz neskoncne zanke
    with clients_lock:
        if username in clients:
            del clients[username]
        for name, client in clients.items():
            send_message(client, {"type": PacketType.user_left, "user": username})
        print("[system] we now have " + str(len(clients)) + " clients")
    client_sock.close()


# kreiraj socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("localhost", PORT))
server_socket.listen(1)

# cakaj na nove odjemalce
print("[system] listening ...")
clients = {}
clients_lock = threading.Lock()

while True:
    try:
        # pocakaj na novo povezavo - blokirajoc klic
        client_sock, client_addr = server_socket.accept()

        thread = threading.Thread(target=client_thread, args=(client_sock, client_addr))
        thread.daemon = True
        thread.start()

    except KeyboardInterrupt:
        break

print("[system] closing server socket ...")
server_socket.close()

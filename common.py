import json
import struct
import socket
import datetime
import enum
import ssl

HEADER_LENGTH = 2


class PacketType(str, enum.Enum):
    init = "init"
    message = "message"
    user_list_init = "user_list_init"
    user_left = "user_left"
    # TODO: more specific errors
    error = "error"


def receive_fixed_length_str(sock: socket.socket, msglen: int):
    message = b""
    while len(message) < msglen:
        chunk = sock.recv(msglen - len(message))  # preberi nekaj bajtov
        if chunk == b"":
            raise RuntimeError("socket connection broken")
        message = message + chunk  # pripni prebrane bajte sporocilu

    return message


def receive_packet(sock: socket.socket):
    header = receive_fixed_length_str(
        sock, HEADER_LENGTH
    )  # preberi glavo sporocila (v prvih 2 bytih je dolzina sporocila)
    packet_length = struct.unpack("!H", header)[0]  # pretvori dolzino sporocila v int

    message = None
    if packet_length > 0:  # ce je vse OK
        message = receive_fixed_length_str(sock, packet_length)  # preberi sporocilo
        message = message.decode("utf-8")
    if not message:
        return message
    obj = json.loads(message)
    return obj


def send_message(sock: socket.socket, message: dict[str, str | int]):
    message["uts"] = str(int(datetime.datetime.now().timestamp()))
    encoded_message = json.dumps(message).encode(
        "utf-8"
    )  # pretvori sporocilo v niz bajtov, uporabi UTF-8 kodno tabelo

    # ustvari glavo v prvih 2 bytih je dolzina sporocila (HEADER_LENGTH)
    # metoda pack "!H" : !=network byte order, H=unsigned short
    header = struct.pack("!H", len(encoded_message))
    full_message = (
        header + encoded_message
    )  # najprj posljemo dolzino sporocilo, slee nato sporocilo samo
    sock.sendall(full_message)

def setup_SSL_context(certfile: str, keyfile: str):
  #uporabi samo TLS, ne SSL
  context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
  # certifikat je obvezen
  context.verify_mode = ssl.CERT_REQUIRED
  #nalozi svoje certifikate
  context.load_cert_chain(certfile=certfile, keyfile=keyfile)
  # nalozi certifikate CAjev, ki jim zaupas
  # (samopodp. cert. = svoja CA!)
  context.load_verify_locations('clients.pem')
  # nastavi SSL CipherSuites (nacin kriptiranja)
  context.set_ciphers('ECDHE-RSA-AES128-GCM-SHA256')
  return context

def get_username_from_conn(conn: ssl.SSLSocket):
    cert = conn.getpeercert()
    if not cert:
        return None
    for sub in cert['subject']:
      for key, value in sub:
        # v commonName je ime uporabnika
        if key == 'commonName':
          return value
    return None

import json
import struct
import socket
import datetime
import enum
import ssl
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID

HEADER_LENGTH = 2


class PacketType(str, enum.Enum):
    init = "init"
    message = "message"
    user_list_init = "user_list_init"
    user_left = "user_left"
    user_joined = "user_joined"
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


def receive_packet(sock: ssl.SSLSocket):
    header = receive_fixed_length_str(
        sock, HEADER_LENGTH
    )  # preberi glavo sporocila (v prvih 2 bytih je dolzina sporocila)
    # pretvori dolzino sporocila v int
    packet_length = struct.unpack("!H", header)[0]

    message = None
    if packet_length > 0:  # ce je vse OK
        message = receive_fixed_length_str(sock, packet_length)  # preberi sporocilo
        message = message.decode("utf-8")
    if not message:
        return message
    obj = json.loads(message)
    return obj


def send_message(sock: ssl.SSLSocket, message: dict[str, str | int | list]):
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


def setup_SSL_context(certfile: str, keyfile: str, certauthsfile: str):
    # uporabi samo TLS, ne SSL
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    # certifikat je obvezen
    context.verify_mode = ssl.CERT_REQUIRED
    # nalozi svoje certifikate
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    # nalozi certifikate CAjev, ki jim zaupas
    # (samopodp. cert. = svoja CA!)
    context.load_verify_locations(certauthsfile)
    # nastavi SSL CipherSuites (nacin kriptiranja)
    context.set_ciphers("ECDHE-RSA-AES128-GCM-SHA256")
    return context


def get_cert_common_name(conn: ssl.SSLSocket):
    cert = conn.getpeercert()
    if not cert:
        raise Exception("Connection does not have a certificate")
    for sub in cert["subject"]:
        for key, value in sub:
            # v commonName je ime uporabnika
            if key == "commonName":
                print("commonName", value)
                return value
    raise Exception("Certificate does not have a 'commonName'")


def get_common_name(certfile: str):
    with open(certfile, "rb") as f:
        cert_data = f.read()
    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    common_name = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    return common_name

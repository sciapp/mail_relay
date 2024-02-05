#!/usr/bin/env python

# The original source code is taken from
# <https://raw.githubusercontent.com/aio-libs/aiosmtpd/ba2b0c3/examples/authenticated_relayer/server.py>
# modified to work with recent aiosmtpd versions (1.4.4.post2) and support STARTTLS for secure connections
#
# Original work licensed under Apache-2.0
# Copyright 2014-2021 The aiosmtpd Developers
#
# Modifications are licensed under the MIT license
# Copyright 2024 Forschungszentrum Juelich GmbH
#
# This code requires at least Python 3.10

import asyncio
import logging
import os
import signal
import ssl
from enum import Enum, auto
from smtplib import SMTP as SMTPCLient
from smtplib import SMTP_SSL as SMTPSSLClient
from typing import Any, Optional

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import AuthResult, LoginPassword

__version_info__ = (0, 1, 0)
__version__ = ".".join(map(str, __version_info__))

logger = logging.getLogger(__name__)


class MailEncryption(Enum):
    NONE = auto()
    STARTTLS = auto()
    TLS = auto()


class DefaultMailPort(Enum):
    PLAIN = 25
    STARTTLS = 587
    TLS = 465


def int_or_none(s: Optional[str]) -> Optional[int]:
    return int(s) if s else None


def none_instead_of_empty(value: Any) -> Any:
    return value if value else None


def str_to_bool(s: Optional[str]) -> bool:
    return s is not None and s.lower() in ("1", "on", "true", "t", "yes", "y")


def get_default_port_from_encryption(encryption: MailEncryption | str) -> DefaultMailPort:
    if isinstance(encryption, str):
        encryption = MailEncryption[encryption]
    return DefaultMailPort[encryption.name]


class THIS_SERVER:
    port = int_or_none(os.environ.get("MAILPROXY_THIS_PORT"))
    encryption = MailEncryption[os.environ.get("MAILPROXY_THIS_ENCRYPTION", "NONE")]
    username = none_instead_of_empty(os.environ.get("MAILPROXY_THIS_USERNAME"))
    password = none_instead_of_empty(os.environ.get("MAILPROXY_THIS_PASSWORD"))
    tls_key_filepath = none_instead_of_empty(os.environ.get("MAILPROXY_THIS_TLS_KEY_FILEPATH"))
    tls_cert_filepath = none_instead_of_empty(os.environ.get("MAILPROXY_THIS_TLS_CERT_FILEPATH"))
    debug = str_to_bool(os.environ.get("MAILPROXY_DEBUG"))


class DEST_SERVER:
    server_name = none_instead_of_empty(os.environ.get("MAILPROXY_DEST_SERVER_NAME"))
    port = int_or_none(os.environ.get("MAILPROXY_DEST_PORT"))
    encryption = MailEncryption[os.environ.get("MAILPROXY_DEST_ENCRYPTION", "NONE")]
    username = none_instead_of_empty(os.environ.get("MAILPROXY_DEST_USERNAME"))
    password = none_instead_of_empty(os.environ.get("MAILPROXY_DEST_PASSWORD"))


class Authenticator:
    def __init__(self, expected_username: str, expected_password: str):
        self._expected_username = expected_username
        self._expected_password = expected_password

    def __call__(self, _server, _session, _envelope, mechanism, auth_data):
        fail_nothandled = AuthResult(success=False, handled=False)
        if mechanism not in ("LOGIN", "PLAIN"):
            return fail_nothandled
        if not isinstance(auth_data, LoginPassword):
            return fail_nothandled
        username = auth_data.login
        password = auth_data.password
        if not (
            username.decode("utf-8") == self._expected_username and password.decode("utf-8") == self._expected_password
        ):
            return fail_nothandled
        return AuthResult(success=True)


class RelayHandler:
    def __init__(
        self,
        server_name: str,
        port: Optional[int],
        encryption: MailEncryption,
        username: Optional[str],
        password: Optional[str],
    ):
        self._server_name = server_name
        self._encryption = encryption
        self._port = port if port is not None else get_default_port_from_encryption(encryption)
        self._username = username
        self._password = password

    async def handle_DATA(self, _server, _session, envelope):
        smtp_class = SMTPSSLClient if self._encryption is MailEncryption.TLS else SMTPCLient
        with smtp_class(self._server_name, self._port) as client:
            logger.info("Relaying mail to %s", self._server_name)
            if self._encryption is MailEncryption.STARTTLS:
                client.starttls()
            if self._username is not None and self._password is not None:
                if self._encryption is MailEncryption.NONE:
                    logger.warning("Sending login credentials without encryption is insecure.")
                client.login(self._username, self._password)
            client.sendmail(from_addr=envelope.mail_from, to_addrs=envelope.rcpt_tos, msg=envelope.original_content)
        return "250 Message accepted for delivery"


def block_until_keyboard_interrupt() -> None:
    loop = asyncio.new_event_loop()
    loop.add_signal_handler(signal.SIGINT, loop.stop)
    loop.run_forever()


def create_mail_relay() -> Controller:
    if DEST_SERVER.server_name is None:
        raise ValueError("Missing environment variable: MAILPROXY_DEST_SERVER_NAME")
    if THIS_SERVER.encryption is MailEncryption.TLS:
        raise ValueError("TLS for incoming connections is not supported by this proxy, use STARTTLS instead.")
    elif THIS_SERVER.encryption is MailEncryption.STARTTLS:
        if THIS_SERVER.tls_key_filepath is None:
            raise ValueError("Missing environment variables: MAILPROXY_THIS_TLS_KEY_FILEPATH")
        if THIS_SERVER.tls_cert_filepath is None:
            raise ValueError("Missing environment variables: MAILPROXY_THIS_TLS_CERT_FILEPATH")
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(THIS_SERVER.tls_cert_filepath, THIS_SERVER.tls_key_filepath)
    else:
        context = None
    handler = RelayHandler(
        DEST_SERVER.server_name,
        DEST_SERVER.port,
        DEST_SERVER.encryption,
        DEST_SERVER.username,
        DEST_SERVER.password,
    )
    auth_required = THIS_SERVER.username is not None and THIS_SERVER.password is not None
    controller = Controller(
        handler,
        hostname="",
        port=THIS_SERVER.port
        if THIS_SERVER.port is not None
        else get_default_port_from_encryption(THIS_SERVER.encryption),
        authenticator=Authenticator(str(THIS_SERVER.username), str(THIS_SERVER.password)) if auth_required else None,
        auth_required=auth_required,
        auth_require_tls=THIS_SERVER.encryption is not MailEncryption.NONE,
        require_starttls=THIS_SERVER.encryption is MailEncryption.STARTTLS,
        tls_context=context,
    )
    return controller


def main() -> None:
    logging.basicConfig(level=logging.DEBUG if THIS_SERVER.debug else logging.INFO)
    controller = create_mail_relay()
    controller.start()
    block_until_keyboard_interrupt()
    print("User abort indicated")
    controller.stop()


if __name__ == "__main__":
    main()

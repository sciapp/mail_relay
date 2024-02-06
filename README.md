# Mail Relay

## Overview

This project provides a simple mail relay server as a Docker image to forward mails to another mail server. It can be
useful in these situations:

- Collect mails from several services and forward them to a central mail server. This way, credentials of the central
  mail server can be kept private and don't need to be shared with the individual services.

- The existing mail server does not provide any interface to interact with an existing service. For example, a service
  could only support sending mail with STARTTLS while an existing mail server only supports TLS or no encryption.

Currently, mail can be received over plain SMTP or over STARTTLS. The target server can be reached over plain SMTP,
STARTTLS or TLS.

## Usage

Prebuilt images are available on [DockerHub](https://hub.docker.com/repository/docker/sciapp/mail_relay/general). Run
the image with Docker and provide the configuration as environment variables to the Docker container.

**Examples:**

- Create a mail relay server which accepts mail without any encryption:

  ```bash
  docker run \
    --detach \
    --rm \
    --name mail_relay \
    -p 8025:25 \
    -e MAILPROXY_THIS_PORT="25" \
    -e MAILPROXY_THIS_ENCRYPTION="NONE" \
    -e MAILPROXY_DEST_SERVER_NAME="smtp.gmail.com" \
    -e MAILPROXY_DEST_PORT="587" \
    -e MAILPROXY_DEST_ENCRYPTION="STARTTLS" \
    -e MAILPROXY_DEST_USERNAME="<username>" \
    -e MAILPROXY_DEST_PASSWORD="<password>" \
    docker.io/sciapp/mail_relay:latest
  ```

  This will accept mails sent with plain SMTP on localhost port 8025 and forward them to Google Mail over STARTTLS.
  Instead of STARTTLS, one could also choose TLS over port 465.

- Create a mail relay server which accepts mail only over STARTTLS but without any authentication:

  ```bash
  docker run \
    --detach \
    --rm \
    --name mail_relay \
    -p 8587:587 \
    -v `pwd`/cert:/etc/ssl/custom_certs:ro
    -e MAILPROXY_THIS_PORT="587" \
    -e MAILPROXY_THIS_ENCRYPTION="STARTTLS" \
    -e MAILPROXY_THIS_TLS_KEY_FILEPATH="/etc/ssl/custom_certs/my.key" \
    -e MAILPROXY_THIS_TLS_CERT_FILEPATH="/etc/ssl/custom_certs/my.pem" \
    -e MAILPROXY_DEST_SERVER_NAME="smtp.gmail.com" \
    -e MAILPROXY_DEST_PORT="587" \
    -e MAILPROXY_DEST_ENCRYPTION="STARTTLS" \
    -e MAILPROXY_DEST_USERNAME="<username>" \
    -e MAILPROXY_DEST_PASSWORD="<password>" \
    docker.io/sciapp/mail_relay:latest
  ```

  This needs a valid SSL certificate bundle to work. In this example, the certificate files are stored in a sub
  directory `cert` in the current working directory.

- Create a mail relay server which accepts mail only over STARTTLS and with correct credentials (`LOGIN` or `PLAIN`
  method):

  ```bash
  docker run \
    --detach \
    --rm \
    --name mail_relay \
    -p 8587:587 \
    -v `pwd`/cert:/etc/ssl/custom_certs:ro
    -e MAILPROXY_THIS_PORT="587" \
    -e MAILPROXY_THIS_ENCRYPTION="STARTTLS" \
    -e MAILPROXY_THIS_TLS_KEY_FILEPATH="/etc/ssl/custom_certs/my.key" \
    -e MAILPROXY_THIS_TLS_CERT_FILEPATH="/etc/ssl/custom_certs/my.pem" \
    -e MAILPROXY_THIS_USERNAME="<username>" \
    -e MAILPROXY_THIS_PASSWORD="<password>" \
    -e MAILPROXY_DEST_SERVER_NAME="smtp.gmail.com" \
    -e MAILPROXY_DEST_PORT="587" \
    -e MAILPROXY_DEST_ENCRYPTION="STARTTLS" \
    -e MAILPROXY_DEST_USERNAME="<username>" \
    -e MAILPROXY_DEST_PASSWORD="<password>" \
    docker.io/sciapp/mail_relay:latest
  ```

For debugging purposes, the environment variable `MAILPROXY_DEBUG` can be set to `1` to enable debug logging.

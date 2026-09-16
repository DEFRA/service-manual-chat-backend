import base64
import os
import ssl
import tempfile
from logging import getLogger

logger = getLogger(__name__)

custom_ca_certs: dict[str, str] = {}
ctx: ssl.SSLContext | None = None


# Custom CA Certificates are passed to services on deployment
# as base64 encoded environment variables with the prefix `TRUSTSTORE_`
def extract_all_certs():
    certs = {}
    for var_name, var_value in os.environ.items():
        if var_name.startswith("TRUSTSTORE_"):
            try:
                decoded_value = base64.b64decode(var_value)
            except base64.binascii.Error as err:
                logger.error("Error decoding value for %s. Skipping. %s", var_name, err)
                continue
            with tempfile.NamedTemporaryFile(
                mode="wb", delete=False, prefix=var_name, suffix=".pem"
            ) as tmp_file:
                tmp_file.write(decoded_value)
                certs[var_name] = tmp_file.name
                logger.error("Wrote %s to %s", var_name, tmp_file.name)
    logger.info("Loaded %d custom certificates", len(certs))
    return certs


def load_certs_into_context(certs):
    ctx = ssl.create_default_context()
    for key in certs:
        try:
            ctx.load_verify_locations(certs[key])
            logger.info("Added %s to truststore", key)
        except Exception as err:
            logger.error("Failed to load cert %s: %s", key, err)
    return ctx


def init_custom_certificates():
    global custom_ca_certs
    global ctx
    logger.info("Initializing custom certificates")
    custom_ca_certs = extract_all_certs()
    ctx = load_certs_into_context(custom_ca_certs)
    return custom_ca_certs


init_custom_certificates()

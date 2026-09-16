import base64
import ssl

from app.common.tls import (
    extract_all_certs,
    init_custom_certificates,
    load_certs_into_context,
)


class TestExtractAllCerts:
    def test_extract_valid_certs(self, mocker, monkeypatch, tmp_path):
        cert_content = b"cert1"
        encoded_cert = base64.b64encode(cert_content).decode()
        monkeypatch.setenv("TRUSTSTORE_CERT1", encoded_cert)

        cert_path = tmp_path / "cert1.pem"

        mock_named_temp_file = mocker.patch(
            "app.common.tls.tempfile.NamedTemporaryFile"
        )
        mock_file_obj = mocker.MagicMock()
        mock_file_obj.name = str(cert_path)
        mock_named_temp_file.return_value.__enter__.return_value = mock_file_obj

        certs = extract_all_certs()

        assert len(certs) == 1
        assert certs["TRUSTSTORE_CERT1"] == str(cert_path)

        # Check if decoded content was written
        mock_file_obj.write.assert_called_once_with(b"cert1")

    def test_extract_invalid_base64_cert(self, monkeypatch):
        monkeypatch.setenv("TRUSTSTORE_BAD", "invalid-base64!")

        certs = extract_all_certs()
        assert len(certs) == 0

    def test_extract_no_truststore_vars(self, monkeypatch):
        monkeypatch.setenv("NORMAL_VAR", "value")

        certs = extract_all_certs()
        assert len(certs) == 0


class TestLoadCertsIntoContext:
    def test_load_valid_certs(self, mocker):
        mock_create_context = mocker.patch("app.common.tls.ssl.create_default_context")
        mock_ctx = mocker.MagicMock()
        mock_create_context.return_value = mock_ctx

        certs = {
            "TRUSTSTORE_1": "/path/to/cert1.pem",
            "TRUSTSTORE_2": "/path/to/cert2.pem",
        }

        ctx = load_certs_into_context(certs)

        assert ctx == mock_ctx
        assert mock_ctx.load_verify_locations.call_count == 2
        mock_ctx.load_verify_locations.assert_any_call("/path/to/cert1.pem")
        mock_ctx.load_verify_locations.assert_any_call("/path/to/cert2.pem")

    def test_load_certs_error(self, mocker):
        mock_create_context = mocker.patch("app.common.tls.ssl.create_default_context")
        mock_ctx = mocker.MagicMock()
        mock_create_context.return_value = mock_ctx
        # Make load_verify_locations raise for the first one
        mock_ctx.load_verify_locations.side_effect = [ssl.SSLError("Bad cert"), None]

        certs = {
            "TRUSTSTORE_BAD": "/path/to/bad.pem",
            "TRUSTSTORE_GOOD": "/path/to/good.pem",
        }

        ctx = load_certs_into_context(certs)

        # Should proceed to load the second one despite error in first
        assert ctx == mock_ctx
        assert mock_ctx.load_verify_locations.call_count == 2


class TestInitCustomCertificates:
    def test_init_globals(self, mocker):
        mock_extract = mocker.patch("app.common.tls.extract_all_certs")
        mock_load = mocker.patch("app.common.tls.load_certs_into_context")

        mock_certs = {"cert": "path"}
        mock_ctx = mocker.MagicMock()

        mock_extract.return_value = mock_certs
        mock_load.return_value = mock_ctx

        result = init_custom_certificates()

        assert result == mock_certs
        mock_extract.assert_called_once()
        mock_load.assert_called_once_with(mock_certs)

        # Check globals are set
        from app.common import tls

        assert tls.custom_ca_certs == mock_certs
        assert tls.ctx == mock_ctx

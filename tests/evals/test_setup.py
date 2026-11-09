"""Where the evaluation finds AWS credentials."""

import pytest

from evals import setup


@pytest.fixture
def home(tmp_path, monkeypatch):
    # The publish runner has AWS credentials in its environment; a test must
    # see none, whatever the machine has.
    for name in ("AWS_PROFILE", *setup.AWS_KEYS, "AWS_BEARER_TOKEN_BEDROCK"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(setup, "CREDENTIALS", tmp_path / "credentials")
    monkeypatch.setattr(setup, "SECRETS", tmp_path / "secrets.env")
    return tmp_path


def test_the_one_profile_in_the_credentials_file_is_used(home):
    (home / "credentials").write_text(
        "[123456789012_example_permissions]\naws_access_key_id = x\n"
    )
    assert setup.aws_profile() == "123456789012_example_permissions"
    assert setup.os.environ["AWS_PROFILE"] == "123456789012_example_permissions"


def test_a_default_profile_is_left_to_boto3(home):
    (home / "credentials").write_text("[default]\n[other]\n")
    assert setup.aws_profile() is None
    assert "AWS_PROFILE" not in setup.os.environ


def test_several_profiles_and_no_default_need_aws_profile(home):
    (home / "credentials").write_text("[one]\n[two]\n")
    with pytest.raises(SystemExit) as stopped:
        setup.aws_profile()
    assert "AWS_PROFILE" in str(stopped.value)
    assert "one, two" in str(stopped.value)


def test_aws_profile_in_the_environment_wins(home, monkeypatch):
    monkeypatch.setenv("AWS_PROFILE", "mine")
    (home / "credentials").write_text("[one]\n")
    assert setup.aws_profile() == "mine"


def test_no_credentials_file_means_no_profile(home):
    assert not (home / "credentials").exists()
    assert setup.aws_profile() is None


def test_secrets_env_fills_the_environment_without_overriding(home, monkeypatch):
    monkeypatch.setenv("AWS_SESSION_TOKEN", "shell")  # noqa: S105 - not a secret
    (home / "secrets.env").write_text(
        "# a comment\nAWS_ACCESS_KEY_ID=key\nAWS_SECRET_ACCESS_KEY=\n"
        "AWS_SESSION_TOKEN=from-the-file\n"
    )
    setup.load_env_file()
    assert setup.os.environ["AWS_ACCESS_KEY_ID"] == "key"
    assert "AWS_SECRET_ACCESS_KEY" not in setup.os.environ
    assert setup.os.environ["AWS_SESSION_TOKEN"] == "shell"  # noqa: S105


def test_the_credentials_file_beats_an_export_in_secrets_env(home):
    (home / "credentials").write_text("[one]\n")
    (home / "secrets.env").write_text(
        "AWS_ACCESS_KEY_ID=stale\nAWS_SECRET_ACCESS_KEY=stale\nOTHER=kept\n"
    )
    setup.load_env_file()
    assert "AWS_ACCESS_KEY_ID" not in setup.os.environ
    assert "AWS_SECRET_ACCESS_KEY" not in setup.os.environ
    assert setup.os.environ["OTHER"] == "kept"


def test_no_credentials_anywhere_stops_with_the_fix(home, monkeypatch):
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(home / "credentials"))
    monkeypatch.setenv("AWS_CONFIG_FILE", str(home / "config"))
    # Without these boto3 would go on to ask the instance metadata service.
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.delenv("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", raising=False)
    monkeypatch.delenv("AWS_CONTAINER_CREDENTIALS_FULL_URI", raising=False)
    with pytest.raises(SystemExit) as stopped:
        setup.check_credentials()
    assert "~/.aws/credentials" in str(stopped.value)

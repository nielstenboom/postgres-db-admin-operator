from unittest.mock import patch, MagicMock
import kubernetes.client.exceptions
import pytest

from postgres_db_admin_operator.k8s import write_credentials_secret

NAMESPACE = "default"
DB_NAME = "my-app-db"
DATA = {"admin-username": "my-app-db_admin", "admin-password": "secret"}


@patch("kubernetes.client.CoreV1Api")
def test_creates_secret(mock_core_v1_class):
    mock_core_v1 = mock_core_v1_class.return_value

    write_credentials_secret(NAMESPACE, DB_NAME, DATA)

    mock_core_v1.create_namespaced_secret.assert_called_once()
    call_args = mock_core_v1.create_namespaced_secret.call_args
    assert call_args.args[0] == NAMESPACE
    secret = call_args.args[1]
    assert secret.metadata.name == f"{DB_NAME}-credentials"
    assert secret.string_data == DATA


@patch("kubernetes.client.CoreV1Api")
def test_replaces_secret_on_conflict(mock_core_v1_class):
    mock_core_v1 = mock_core_v1_class.return_value
    mock_core_v1.create_namespaced_secret.side_effect = kubernetes.client.exceptions.ApiException(status=409)

    write_credentials_secret(NAMESPACE, DB_NAME, DATA)

    mock_core_v1.replace_namespaced_secret.assert_called_once()
    call_args = mock_core_v1.replace_namespaced_secret.call_args
    assert call_args.args[0] == f"{DB_NAME}-credentials"
    assert call_args.args[1] == NAMESPACE


@patch("kubernetes.client.CoreV1Api")
def test_propagates_non_conflict_api_errors(mock_core_v1_class):
    mock_core_v1 = mock_core_v1_class.return_value
    mock_core_v1.create_namespaced_secret.side_effect = kubernetes.client.exceptions.ApiException(status=403)

    with pytest.raises(kubernetes.client.exceptions.ApiException):
        write_credentials_secret(NAMESPACE, DB_NAME, DATA)

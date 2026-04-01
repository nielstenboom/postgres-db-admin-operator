import kubernetes


def write_credentials_secret(namespace: str, name: str, data: dict[str, str]) -> None:
    core_v1 = kubernetes.client.CoreV1Api()
    secret = kubernetes.client.V1Secret(
        metadata=kubernetes.client.V1ObjectMeta(name=f"{name}-credentials", namespace=namespace),
        string_data=data,
    )
    try:
        core_v1.create_namespaced_secret(namespace, secret)
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 409:
            core_v1.replace_namespaced_secret(f"{name}-credentials", namespace, secret)
        else:
            raise

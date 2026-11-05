output "registry_id" {
  value = yandex_container_registry.registry.id
}

# 👈 Добавляем вывод ID сервисного аккаунта
output "sa_id" {
  value = yandex_iam_service_account.registry_sa.id
}

output "sa_key_json" {
  value = jsonencode({
    id                 = yandex_iam_service_account_key.registry_key.id
    service_account_id = yandex_iam_service_account_key.registry_key.service_account_id
    private_key        = yandex_iam_service_account_key.registry_key.private_key
  })
  sensitive = true
}
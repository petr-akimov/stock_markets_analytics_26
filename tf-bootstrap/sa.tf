resource "random_id" "sa_id" {
  byte_length = 4
}

resource "yandex_iam_service_account" "registry_sa" {
  name = "registry-sa-${random_id.sa_id.hex}"
}

resource "yandex_resourcemanager_folder_iam_member" "registry_push" {
  folder_id = var.yc_folder_id
  role      = "container-registry.images.pusher"
  member    = "serviceAccount:${yandex_iam_service_account.registry_sa.id}"
}

# 👈 Добавляем права на вытягивание (pull) образов для этого же сервисного аккаунта
resource "yandex_resourcemanager_folder_iam_member" "registry_pull" {
  folder_id = var.yc_folder_id
  role      = "container-registry.images.puller"
  member    = "serviceAccount:${yandex_iam_service_account.registry_sa.id}"
}

resource "yandex_iam_service_account_key" "registry_key" {
  service_account_id = yandex_iam_service_account.registry_sa.id
  description        = "key for docker push"
}
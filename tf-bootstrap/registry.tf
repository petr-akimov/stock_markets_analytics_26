resource "random_id" "registry_id" {
  byte_length = 4
}

resource "yandex_container_registry" "registry" {
  name = "otus-registry-${random_id.registry_id.hex}"
}
# Prompt Center

Bu klasör BGTS içindeki tüm kanonik LLM prompt kaynaklarını merkezi olarak tutar.

Yapı:

- `manifest.json`: Hangi prompt'un hangi parçalardan oluştuğunu tanımlar.
- `policies/`: Tüm görevlerde yeniden kullanılan ortak kalite kuralları.
- `tasks/`: AI Gateway `TaskType` bazlı görev prompt parçaları.
- `engine/`: Engine servisleri için görev-özel prompt parçaları.

Amaç:

- Prompt kurallarını tek yerden yönetmek
- Gateway ve engine tarafında tonu ve kalite çıtasını eşitlemek
- Değişiklikleri testlerle daha kolay doğrulamak
- Yeni prompt eklemeyi deklaratif hale getirmek

# DEPRECATED - Engine Feature Dosyalari

**Bu dizindeki .feature dosyalari artik kanonik BDD kaynak degildir.**

## Yeni Konum

Tum BDD feature dosyalari artik `e2e/bdd/features/` altinda yonetilmektedir:

```
e2e/bdd/features/
├── auth/           -> login.feature
├── projects/       -> project_management.feature
├── scenarios/      -> scenario_management.feature
├── executions/     -> execution_management.feature
├── flows/          -> flow_management.feature
├── approvals/      -> approval_queue.feature
├── import/         -> import_tests.feature
├── regression/     -> regression_sets.feature
└── common/         -> navigation.feature, accessibility.feature
```

## Bu dizin neden hala var?

- `engine/steps/` Python step definitions henuz bu feature'lara referans veriyor
- `engine/tests/e2e/` pytest-bdd testleri bu feature'lari kullaniyor
- Tam goc tamamlandiginda bu dizin silinecektir

## Yeni test yazarken

**YENI FEATURE DOSYASI EKLEMEYIN.** Yeni BDD testleri `e2e/bdd/features/` altina yazin.

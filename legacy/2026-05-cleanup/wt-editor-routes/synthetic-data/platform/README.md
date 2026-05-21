# SyntheticBankData

Bu klasör sentetik banka verisi ve ilgili deneme projeleri için kullanılır.

## Claude worktree kopyaları

`.claude/worktrees/` altındaki dizinler **IDE/worktree artefaktıdır**; ana sentetik veri motoru repoda [`../engine/ai_synthetic_data/`](../engine/ai_synthetic_data/) içindedir.

Worktree kopyaları repoda tutulmaz (bkz. kök `.gitignore`). Yerelde oluşursa güvenle silinebilir.

## Kanonik kod

- Üretim ve geliştirme: `engine/ai_synthetic_data/`
- API: `backend/` (TSPM ve proxy)

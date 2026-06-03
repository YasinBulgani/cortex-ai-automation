"""Kiwi TCMS integration domain.

Import-only sync (Kiwi → Neurex Management). A per-project ``KiwiConnection``
holds the (Fernet-encrypted) credentials; ``service.run_sync`` pulls objects via
Kiwi's JSON-RPC API, maps them with the pure helpers in ``mappers`` and upserts
into the existing ``test_management`` models. ``KiwiIdMap`` keeps the external↔
internal id mapping so re-syncs are idempotent and a future two-way sync has a
foundation.
"""

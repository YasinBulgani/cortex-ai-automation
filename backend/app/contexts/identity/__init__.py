"""
Identity Bounded Context.

Sorumlulukları:
- User, Role, Permission aggregate'leri
- Authentication & session
- RBAC (Role-Based Access Control)
- Tenant'a bağlı identity

NOT içermez:
- Project sahipliği (Projects context'inde)
- Audit log writing (Audit context'inde — Identity event publish eder)
"""

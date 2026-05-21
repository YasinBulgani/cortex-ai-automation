"""
Projects Bounded Context.

Sorumlulukları:
- Project aggregate (yaşam döngüsü, ayarlar)
- ProjectMembership (kim hangi projeye erişiyor)
- Project archival + restoration
- Product family attribution (Mobile, Web, Service, ...)

NOT içermez:
- User CRUD (Identity context'i)
- Scenario CRUD (Scenarios context'i)
- Test execution (Execution context'i)

Cross-context iletişim domain events üzerinden:
- ProjectCreated → Audit log + Analytics
- ProjectArchived → Cleanup workers
- ProjectMemberAdded → Notifications
"""

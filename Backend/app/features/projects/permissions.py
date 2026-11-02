"""Per-project permissions a team leader/admin can delegate to a project member (`project_memberships.permissions`).

Team leaders and admins always hold all of them. Managing members and delegating permissions is never delegable,
so nobody can raise their own access."""

DOCUMENTS = "documents"  # upload, delete, rename, move/copy, folders, retry/cancel in the file manager
MEMORY = "memory"  # create/edit/delete the project's memory facts

PROJECT_PERMISSIONS: tuple[str, ...] = (DOCUMENTS, MEMORY)

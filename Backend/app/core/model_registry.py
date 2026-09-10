"""Imports every feature's models so they register on `Base.metadata`.

Needed by Alembic autogenerate and by SQLAlchemy relationship string
resolution (e.g. `User.team_memberships` referencing `TeamMembership`),
since features never import each other's models directly.
"""

from app.features.access_control import models as _access_control_models  # noqa: F401
from app.features.auth import models as _auth_models  # noqa: F401
from app.features.chat import models as _chat_models  # noqa: F401
from app.features.documents import models as _documents_models  # noqa: F401
from app.features.projects import models as _projects_models  # noqa: F401

__all__: list[str] = []

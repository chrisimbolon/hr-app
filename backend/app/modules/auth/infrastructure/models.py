"""
auth/infrastructure/models.py
──────────────────────────────
Auth module has NO dedicated models.

The Employee, DeviceRegistration models in employee/infrastructure/models.py
ARE the auth data source. Auth is a behaviour (login/logout/token), not an
entity — so it doesn't own its own tables.

This file exists to keep the package structure consistent, and to document
this decision explicitly so no one creates a duplicate UserModel here.

Old SQLModel tables (usermodel, credentialmodel, usertenantmodel) that were
created by a previous version must be dropped manually:

    psql -U hr_user -d hr_db -c "DROP TABLE IF EXISTS usertenantmodel, credentialmodel, usermodel CASCADE;"
"""


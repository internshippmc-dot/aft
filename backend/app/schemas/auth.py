from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    # Only required once the account has completed TOTP enrollment — see
    # auth.py's login handler. Omitted/blank for accounts without 2FA set up.
    totp_code: str | None = None


class MeResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    totp_enrolled: bool


class TotpEnrollStartOut(BaseModel):
    secret: str
    provisioning_uri: str


class TotpConfirmIn(BaseModel):
    code: str


class TotpDisableIn(BaseModel):
    # Re-proves the account is still in the right hands before turning 2FA
    # off — otherwise a stolen/left-open session could disable it silently.
    password: str

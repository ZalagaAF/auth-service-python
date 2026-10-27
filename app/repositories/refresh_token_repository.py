import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.refresh_tokens import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(token)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise
        self.session.refresh(token)
        return token

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        consulta = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return self.session.scalar(consulta)

    def rotate(
        self,
        token: RefreshToken,
        new_token_hash: str,
        new_expires_at: datetime,
    ) -> RefreshToken | None:
        ahora = datetime.now(timezone.utc)

        # El UPDATE solo toca la fila si sigue sin revocar. Si dos requests llegan
        # a la vez con el mismo token, la base deja pasar solo a uno.
        resultado = self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=ahora)
        )
        if resultado.rowcount == 0:
            self.session.rollback()
            return None

        nuevo = RefreshToken(
            user_id=token.user_id,
            token_hash=new_token_hash,
            expires_at=new_expires_at,
        )
        self.session.add(nuevo)
        try:
            # Un único commit: revocar el viejo y crear el nuevo, o ninguno de los dos.
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise
        self.session.refresh(nuevo)
        return nuevo

    def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        ahora = datetime.now(timezone.utc)

        # Solo los que siguen activos: a los ya revocados no se les pisa la fecha.
        resultado = self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=ahora)
        )
        cantidad = resultado.rowcount
        self.session.commit()
        return cantidad
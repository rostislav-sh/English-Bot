from typing import Annotated

from fastapi import Depends, HTTPException, status

from .auth import get_current_payload


async def get_current_user_id_from_access_token(
    payload: Annotated[dict, Depends(get_current_payload)],
) -> int:
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        return int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

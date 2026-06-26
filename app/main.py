from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from contextlib import asynccontextmanager
import uuid
from datetime import timedelta
from sqlalchemy import select, func, delete

from app.models.db import init_db, get_db, User, Case
from app.models.schemas import UserCreate, Token, CaseCreate, CaseOut
from app.utils.auth import (
    verify_password, get_password_hash,
    create_access_token, get_current_user,
)

from app.models.db import init_db, get_db, User, Case, Document  # add Document
from sqlalchemy import select, func                               # add func
from dotenv import load_dotenv
load_dotenv()  # must be before any other app imports




@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Judiciary AI API", lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    tb = traceback.format_exc()
    print("UNHANDLED ERROR:", tb)  # prints to uvicorn terminal
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": tb}
    )

# Register routers AFTER app is created
from app.routers import upload, analysis, dashboard
app.include_router(upload.router)
app.include_router(analysis.router)
app.include_router(dashboard.router)


@app.post("/auth/register", response_model=Token)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Username already taken")
    user = User(
        id=str(uuid.uuid4()),
        username=data.username,
        hashed_password=get_password_hash(data.password),
    )
    db.add(user)
    await db.commit()
    token = create_access_token({"sub": user.id}, timedelta(days=30))
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token({"sub": user.id}, timedelta(days=30))
    return {"access_token": token, "token_type": "bearer"}


# @app.post("/cases", response_model=CaseOut)
# async def create_case(
#     data: CaseCreate,
#     user=Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     case = Case(
#         id=str(uuid.uuid4()),
#         user_id=user.id,
#         title=data.title,
#         description=data.description,
#     )
#     db.add(case)
#     await db.commit()
#     await db.refresh(case)
#     return CaseOut(
#         id=case.id, title=case.title,
#         description=case.description, created_at=case.created_at,
#     )


# @app.get("/cases", response_model=list[CaseOut])
# async def list_cases(
#     user=Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     result = await db.execute(select(Case).where(Case.user_id == user.id))
#     cases  = result.scalars().all()

#     output = []
#     for c in cases:
#         count_res = await db.execute(
#             select(func.count(Document.id)).where(Document.case_id == c.id)
#         )
#         doc_count = count_res.scalar() or 0

#         last_res = await db.execute(
#             select(Document.uploaded_at)
#             .where(Document.case_id == c.id)
#             .order_by(Document.uploaded_at.desc())
#             .limit(1)
#         )
#         last_upload = last_res.scalar()

#         output.append(CaseOut(
#             id=c.id,
#             title=c.title,
#             description=c.description,
#             created_at=c.created_at,
#             document_count=doc_count,
#             last_activity=last_upload.isoformat() if last_upload else None,
#         ))
#     return output

@app.post("/cases", response_model=CaseOut)
async def create_case(
    data: CaseCreate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    case = Case(
        id=str(uuid.uuid4()),
        user_id=user.id,
        title=data.title,
        description=data.description,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return CaseOut(
        id=case.id,
        title=case.title,
        description=case.description,
        created_at=case.created_at,
        document_count=0,
        last_activity=None,
    )


@app.delete("/cases/{case_id}")
async def delete_case(
    case_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user.id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(404, "Case not found or access denied")

    # delete documents belonging to this case first, so you don't leave orphans
    await db.execute(delete(Document).where(Document.case_id == case_id))
    await db.execute(delete(Case).where(Case.id == case_id))
    await db.commit()

    return {"message": f"Case '{case.title}' deleted successfully"}


from app.services.statute_identifier import get_model_status, is_model_loaded

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "statute_model": get_model_status(),
    }

# Warm up the model on startup (optional but recommended)
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await init_db()
#     # Pre-load LeSICiN in background so first request isn't slow
#     import asyncio
#     from app.services.statute_identifier import _ensure_loaded
#     asyncio.create_task(_ensure_loaded())
#     yield


# 1. Remove the SECOND lifespan definition at the bottom entirely — delete these lines:
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await init_db()
#     import asyncio
#     from app.services.statute_identifier import _ensure_loaded
#     asyncio.create_task(_ensure_loaded())
#     yield

# 2. Replace the FIRST lifespan with this (adds model warmup):
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    import asyncio
    from app.services.statute_identifier import _ensure_loaded
    asyncio.create_task(_ensure_loaded())
    yield

# 3. Replace list_cases entirely:
from sqlalchemy import select, func
from app.models.db import Document  # add Document to existing import

@app.get("/cases", response_model=list[CaseOut])
async def list_cases(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Case).where(Case.user_id == user.id))
    cases  = result.scalars().all()

    output = []
    for c in cases:
        count_res = await db.execute(
            select(func.count(Document.id)).where(Document.case_id == c.id)
        )
        doc_count = count_res.scalar() or 0

        last_res = await db.execute(
            select(Document.uploaded_at)
            .where(Document.case_id == c.id)
            .order_by(Document.uploaded_at.desc())
            .limit(1)
        )
        last_upload = last_res.scalar()

        output.append(CaseOut(
            id=c.id,
            title=c.title,
            description=c.description,
            created_at=c.created_at,
            document_count=doc_count,
            last_activity=last_upload.isoformat() if last_upload else None,
        ))
    return output
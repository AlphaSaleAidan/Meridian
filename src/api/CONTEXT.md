# src/api/ — FastAPI Application

Entry point: `app.py` (registers all routers, CORS, lifespan)
Routes in: `routes/` (18 modules, each has its own `router = APIRouter(prefix="/api/...")`)

## Adding a route
1. Create `routes/your_route.py` with `router = APIRouter(prefix="/api/yours")`
2. Import in `app.py`: `from .routes.your_route import router as your_router`
3. Register: `app.include_router(your_router)`

## Auth pattern
Most endpoints extract org_id from Supabase JWT via auth dependency.
Always scope data queries to org_id.

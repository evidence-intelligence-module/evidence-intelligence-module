"""Evidence Request Interface (HLD §3) — the sole external interface this
module exposes (Constitution §5). App factory pattern so tests can construct
isolated app instances."""

from fastapi import FastAPI

from evidence_intelligence.api.middleware import RequestLoggingMiddleware


def create_app() -> FastAPI:
    app = FastAPI(
        title="Evidence Intelligence Module",
        description="Generic evidence-request interface for crop-loss evidence generation.",
        version="0.1.0",
    )
    app.add_middleware(RequestLoggingMiddleware)

    from evidence_intelligence.api.routes import router

    app.include_router(router)
    return app


app = create_app()

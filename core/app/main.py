import logging
from fastapi import FastAPI, APIRouter, Depends
from typing import Dict, Any, Annotated, Union
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from .state_manager import state_manager
from .module_loader import ModuleLoader
from .api import create_api_routes
from .api_v2 import create_api_routes_v2
from .auth import router as auth_router, get_current_user, get_current_user_or_service
from .models import User
from .database_compat import create_db_and_tables
from sqlmodel import Session
from .init_db import init_db
from .content_pack_manager import ContentPackManager
from .logging_config import setup_logging
from .modules.timeline.tool import router as timeline_router
from .middleware import AuthenticationMiddleware, RateLimitHeaderMiddleware, RequestLoggingMiddleware
from .rate_limiter import limiter, custom_rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .version_manager import VersionMiddleware, create_version_router

# Apply the JSON logging configuration at the earliest point
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # This code runs on server startup
    logging.info("--- IntentVerse Core Engine Starting Up ---")

    # Skip database initialization during tests
    import os

    is_testing = os.getenv("SERVICE_API_KEY") == "test-service-key-12345"

    if not is_testing:
        create_db_and_tables()
        # Initialize the database with default data (admin user and groups)
        init_db()
    else:
        logging.info("Skipping database initialization during tests")

    # Discover and load all modules from the 'modules' directory
    if not is_testing:
        from .database_compat import get_session

        for session in get_session():
            module_loader.load_modules(session)
            break
    else:
        logging.info("Skipping module loading during tests")

    # Load default content pack after modules are loaded
    if not is_testing:
        content_pack_manager.load_default_content_pack()
    else:
        logging.info("Skipping content pack loading during tests")

    # Log system startup event (skip during tests to avoid database issues)
    if not is_testing:
        from .modules.timeline.tool import log_system_event

        log_system_event(
            title="Core Service Started",
            description="The IntentVerse Core Engine has been started and is ready to accept connections.",
        )
        logging.info("Logged system startup event")
    else:
        logging.info("Skipping startup event logging during tests")

    yield
    # This code runs on server shutdown
    logging.info("--- IntentVerse Core Engine Shutting Down ---")

    # Log system shutdown event (skip during tests to avoid database issues)
    import os
    is_testing = os.getenv("SERVICE_API_KEY") == "test-service-key-12345"
    
    if not is_testing:
        try:
            from .modules.timeline.tool import log_system_event

            log_system_event(
                title="Core Service Stopped",
                description="The IntentVerse Core Engine has been stopped.",
            )
            logging.info("Logged system shutdown event")
        except Exception as e:
            logging.error(f"Failed to log shutdown event: {e}")
    else:
        logging.info("Skipping shutdown event logging during tests")


# --- Application Initialization ---
app = FastAPI(
    title="IntentVerse Core Engine",
    description="Manages state, tools, and logic for the IntentVerse simulation.",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Add CORS middleware to allow cross-origin requests from the web client
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Add authentication middleware (must be first to set user state)
app.add_middleware(AuthenticationMiddleware)

# Add rate limiting header middleware
app.add_middleware(RateLimitHeaderMiddleware)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add API versioning middleware
app.add_middleware(VersionMiddleware)

# Add the rate limiter to the app
# Rate limits are configured as follows:
# - 30 requests per minute for unauthenticated users
# - 100 requests per minute for authenticated users
# - 200 requests per minute for admin users and service accounts
# These limits can be configured via environment variables:
# - RATE_LIMIT_UNAUTH: Rate limit for unauthenticated users (default: 30/minute)
# - RATE_LIMIT_AUTH: Rate limit for authenticated users (default: 100/minute)
# - RATE_LIMIT_ADMIN: Rate limit for admin users and services (default: 200/minute)
app.state.limiter = limiter

# Add custom rate limit exceeded handler
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)

module_loader = ModuleLoader(state_manager)
content_pack_manager = ContentPackManager(state_manager, module_loader)

# Create the API routes for different versions
api_router_v1 = create_api_routes(module_loader, content_pack_manager)
api_router_v2 = create_api_routes_v2(module_loader, content_pack_manager)

# Add version information router
version_router = create_version_router()
app.include_router(version_router)

# Add API routers for different versions
app.include_router(api_router_v1)
app.include_router(api_router_v2)
app.include_router(auth_router)
app.include_router(timeline_router)

# Create a new, separate router for debug endpoints
debug_router = APIRouter()


@debug_router.get("/debug/module-loader-state", tags=["Debug"])
def get_module_loader_state(
    current_user_or_service: Annotated[
        Union[User, str], Depends(get_current_user_or_service)
    ],
):
    """
    Returns a snapshot of the ModuleLoader's state for debugging purposes.
    This allows us to see from the outside what the server sees on the inside.
    Only available to authenticated users.
    """
    return {
        "modules_path_calculated": str(module_loader.modules_path),
        "modules_path_exists": module_loader.modules_path.exists(),
        "loading_errors": module_loader.errors,
        "loaded_modules": list(module_loader.modules.keys()),
    }


app.include_router(debug_router, prefix="/api/v1")


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root():
    """
    A simple root endpoint to confirm the server is running.
    """
    return {"message": "Welcome to the IntentVerse Core Engine"}

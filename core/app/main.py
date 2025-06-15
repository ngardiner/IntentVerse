from fastapi import FastAPI, APIRouter
from typing import Dict, Any
from contextlib import asynccontextmanager

from .state_manager import StateManager
from .module_loader import ModuleLoader
from .api import create_api_routes
from .auth import router as auth_router
from .database import create_db_and_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This code runs on server startup
    print("--- IntentVerse Core Engine Starting Up ---")
    create_db_and_tables()
    # Discover and load all modules from the 'modules' directory
    loader.load_modules()
    yield
    # This code runs on server shutdown
    print("--- IntentVerse Core Engine Shutting Down ---")

# --- Application Initialization ---
app = FastAPI(
    title="IntentVerse Core Engine",
    description="Manages state, tools, and logic for the IntentVerse simulation.",
    version="0.1.0",
    lifespan=lifespan,
)

state_manager = StateManager()
loader = ModuleLoader(state_manager)
loader.load_modules()

# Create the main API routes, passing the loader to them.
api_router = create_api_routes(loader)
app.include_router(api_router, prefix="/api/v1")
app.include_router(auth_router)

# Create a new, separate router for debug endpoints
debug_router = APIRouter()

@debug_router.get("/debug/module-loader-state", tags=["Debug"])
def get_module_loader_state():
    """
    Returns a snapshot of the ModuleLoader's state for debugging purposes.
    This allows us to see from the outside what the server sees on the inside.
    """
    return {
        "modules_path_calculated": str(loader.modules_path),
        "modules_path_exists": loader.modules_path.exists(),
        "loading_errors": loader.errors,
        "loaded_modules": list(loader.modules.keys())
    }

app.include_router(debug_router, prefix="/api/v1")


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root():
    """
    A simple root endpoint to confirm the server is running.
    """
    return {"message": "Welcome to the IntentVerse Core Engine"}
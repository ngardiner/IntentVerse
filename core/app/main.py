from fastapi import FastAPI
from .state_manager import state_manager
from .module_loader import ModuleLoader
from .api import create_api_routes

# --- Application Initialization ---

# Create the main FastAPI application instance
app = FastAPI(title="IntentVerse Core Engine")

# Create a single instance of the ModuleLoader and pass the shared state_manager
loader = ModuleLoader(state_manager)

# Discover and load all modules from the 'modules' directory
loader.load_modules()

# Create the API routes and pass the loader instance to it
api_router = create_api_routes(loader)

# Include the API router in our main application
app.include_router(api_router)


# --- Root Endpoint ---

@app.get("/")
def read_root():
    """
    A simple root endpoint to confirm the server is running.
    """
    return {"message": "IntentVerse Core Engine is running."}

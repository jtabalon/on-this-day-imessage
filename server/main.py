"""FastAPI application — On This Day iMessage."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server.contacts import load_contacts
from server.routes.conversations import router as conversations_router
from server.routes.messages import router as messages_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load contacts at startup
    load_contacts()
    yield


app = FastAPI(title="On This Day iMessage", lifespan=lifespan)

# API routes
app.include_router(conversations_router, prefix="/api")
app.include_router(messages_router, prefix="/api")

# Serve static files (HTML/CSS/JS) at root
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

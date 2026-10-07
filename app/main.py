from fastapi import FastAPI, Request
import time
from .database import lifespan
from .routers import users, organizations,admin, memberships, documents
from .routers.auth import router as auth_router

app = FastAPI(lifespan=lifespan, title="QueryDoc API")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()

    response = await call_next(request)

    process_time = (time.perf_counter() - start_time) * 1000

    print(f"Path: {request.url.path} | Duration: {process_time:.2f}ms")
    return response



@app.get("/")
def root():
    return {"Message": "Welcome to the QueryDoc API"}

app.include_router(auth_router)
app.include_router(users.router)
app.include_router(organizations.router)
app.include_router(memberships.router)
app.include_router(documents.router)

#Disabled to prevent displaying in the API docs
#app.include_router(admin.router)


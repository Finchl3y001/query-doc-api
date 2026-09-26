from fastapi import FastAPI
from .database import lifespan
from .routers import users, organizations,admin, memberships

app = FastAPI(lifespan=lifespan, title="QueryDoc API")

app.include_router(users.router)
app.include_router(organizations.router)
app.include_router(memberships.router)

#Disabled to prevent displaying in the API docs
#app.include_router(admin.router)

@app.get("/")
def root():
    return {"Message": "Welcome to the QueryDoc API"}
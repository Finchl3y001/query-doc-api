from sqlmodel import SQLModel, Field, Relationship
#from datetime import datetime

class MembershipBase(SQLModel):
    role: str

class Membership(MembershipBase, table=True):
    __tablename__ = "memberships"

    id: int = Field(default = None, primary_key = True)
    user_id: int = Field(default=None, foreign_key="users.id")
    organization_id: int = Field(default=None, foreign_key="organizations.id")

    created_at: str
    #created_at: datetime = Field(default_factory=datetime.utcnow)


class UserBase(SQLModel):
    email: str
    password_hash: str
    created_at: str

class User(UserBase, table = True):
    __tablename__ = "users"

    id: int | None = Field(default = None, primary_key = True)

    organizations: list["Organization"] = Relationship(back_populates="users", link_model=Membership)


class OrganizationBase(SQLModel):
    name: str
    created_at: str

class Organization(OrganizationBase, table=True):
    __tablename__ = "organizations"

    id: int = Field(default = None, primary_key = True)

    users: list["User"] = Relationship(back_populates="organizations", link_model=Membership)
from sqlmodel import SQLModel, Field, Relationship
from pydantic import EmailStr
from datetime import datetime, timezone
from enum import Enum
import uuid
from sqlalchemy import Column, JSON

class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"

class MembershipBase(SQLModel):
    role: UserRole = Field(default=UserRole.MEMBER)

class Membership(MembershipBase, table=True):
    __tablename__ = "memberships"

    id: int | None = Field(default = None, primary_key = True)

    user_id: int = Field(default=None, foreign_key="users.id")
    organization_id: int = Field(default=None, foreign_key="organizations.id")
    
    #created_at: datetime = Field(default_factory=datetime.utcnow) -- deprecated
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MembershipCreate(SQLModel):
    user_id: int
    organization_id: int
    role: str = Field(default="member", description="admin, user, member")

class MembershipUpdate(SQLModel):
    role: str | None = None

class MembershipResponse(MembershipBase):
    id: int
    user_id: int
    organization_id: int
    created_at: datetime


class UserBase(SQLModel):
    username: str
    email: EmailStr

class User(UserBase, table = True):
    __tablename__ = "users"

    id: int | None = Field(default = None, primary_key = True)

    username: str = Field(unique=True, index=True)
    email: EmailStr = Field(unique=True, index=True)
    password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
   #created_at: datetime = Field(default_factory=datetime.utcnow)

    organizations: list["Organization"] = Relationship(back_populates="users", link_model=Membership)

class UserCreate(SQLModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr 
    password: str = Field(..., min_length=8)

class UserUpdate(SQLModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)

class UserResponse(UserBase):
    id: int
    created_at: datetime


class OrganizationBase(SQLModel):
    name: str
    

class Organization(OrganizationBase, table=True):
    __tablename__ = "organizations"

    id: int | None = Field(default = None, primary_key = True)
    name: str = Field(unique=True, index = True)

    #created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    users: list["User"] = Relationship(back_populates="organizations", link_model=Membership)

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(SQLModel):
    name: str | None = None

class OrganizationResponse(OrganizationBase):
    id: int
    created_at: datetime


class OrganizationWorkspaceInfo(SQLModel):
    id: int
    name: str
    role: UserRole  # Tells the frontend if they are an admin, manager, or member
    joined_at: datetime

class UserProfileResponse(UserBase):
    id: int
    created_at: datetime
    organizations: list["OrganizationWorkspaceInfo"] = []


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"

class DocumentBase(SQLModel):
    filename: str
    storage_path: str

class Document(DocumentBase, table = True):
    __tablename__ = "documents"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    organization_id: int = Field(foreign_key="organizations.id")
    uploaded_by: int =Field(foreign_key="users.id")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    #Optional rships for cleaner querying
    organization: "Organization" = Relationship()
    uploader: "User" = Relationship()

    file_hash: str = Field(index = True)

class DocumentResponse(DocumentBase):
    id: uuid.UUID
    organization_id: int
    created_at: datetime

# Add this to your app/models.py file

class DocumentChunk(SQLModel, table=True):
    __tablename__ = "document_chunks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(foreign_key="documents.id", ondelete="CASCADE")
    organization_id: int = Field(foreign_key="organizations.id", index=True)
    
    content: str = Field(description="The actual snippet of text from the file")
    
    # FIX: Explicitly instruct SQLModel to store the list data inside a JSON column format!
    embedding: list[float] = Field(
        sa_column=Column(JSON), 
        description="1024-dimension float list from Mistral"
    )


'''
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
'''
"""
Base CRUD (Create, Read, Update, Delete) operations.
Based on the Full Stack FastAPI Template pattern.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
import uuid

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlmodel import SQLModel

# Define generic types for SQLModel, Create Schema, and Update Schema
ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base class for CRUD operations.
    
    Provides standard create, read, update, and delete methods.
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Initialize with SQLModel model class.
        
        Args:
            model: A SQLModel model class
        """
        self.model = model
    
    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """
        Get a single record by ID.
        
        Args:
            db: Database session
            id: ID of the record to get
            
        Returns:
            The record if found, None otherwise
        """
        return await db.get(self.model, id)
    
    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """
        Get multiple records with pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of records
        """
        statement = select(self.model).offset(skip).limit(limit)
        results = await db.execute(statement)
        return results.scalars().all()
    
    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new record.
        
        Args:
            db: Database session
            obj_in: Create schema with the data to create
            
        Returns:
            The created record
        """
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)  # type: ignore
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Update a record.
        
        Args:
            db: Database session
            db_obj: Database object to update
            obj_in: Update schema or dict with the data to update
            
        Returns:
            The updated record
        """
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def remove(self, db: AsyncSession, *, id: Any) -> Optional[ModelType]:
        """
        Delete a record.
        
        Args:
            db: Database session
            id: ID of the record to delete
            
        Returns:
            The deleted record if found, None otherwise
        """
        obj = await db.get(self.model, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj
    
    async def get_by_field(
        self, db: AsyncSession, field_name: str, value: Any
    ) -> Optional[ModelType]:
        """
        Get a single record by a specific field value.
        
        Args:
            db: Database session
            field_name: Name of the field to filter by
            value: Value to filter for
            
        Returns:
            The record if found, None otherwise
        """
        statement = select(self.model).where(getattr(self.model, field_name) == value)
        results = await db.execute(statement)
        return results.scalar_one_or_none()
    
    async def exists(self, db: AsyncSession, id: Any) -> bool:
        """
        Check if a record exists.
        
        Args:
            db: Database session
            id: ID of the record to check
            
        Returns:
            True if the record exists, False otherwise
        """
        obj = await db.get(self.model, id)
        return obj is not None

from typing import List, Optional
from uuid import UUID
import asyncpg
from platform.core.domain.project import Project
from platform.adapters.database.base_repository import BaseRepository

class ProjectRepository(BaseRepository[Project]):
    """Repository for managing project persistence"""
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self._pool = connection_pool
    
    async def create(self, project: Project) -> Project:
        """Create a new project in the database"""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO projects (
                    id, name, description, goal_text, status, owner_id,
                    requirements, constraints, assumptions, acceptance_criteria,
                    capabilities_needed, team_plan, execution_plan,
                    created_at, updated_at, schema_version
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            """, 
                project.id,
                project.name,
                project.description,
                project.goal.text,
                project.status.value,
                project.owner_id,
                project.requirements,
                project.constraints,
                project.assumptions,
                project.acceptance_criteria,
                project.capabilities_needed,
                project.team_plan,
                project.execution_plan,
                project.created_at,
                project.updated_at,
                project.schema_version
            )
            
        return project
    
    async def get_by_id(self, id: UUID) -> Optional[Project]:
        """Retrieve a project by its ID"""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    id, name, description, goal_text, status, owner_id,
                    requirements, constraints, assumptions, acceptance_criteria,
                    capabilities_needed, team_plan, execution_plan,
                    created_at, updated_at, schema_version
                FROM projects WHERE id = $1
            """, id)
            
            if not row:
                return None
            
            # Convert back to Project model
            return Project(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                goal=ProjectGoal(text=row['goal_text']),
                status=row['status'],
                owner_id=row['owner_id'],
                requirements=row['requirements'],
                constraints=row['constraints'],
                assumptions=row['assumptions'],
                acceptance_criteria=row['acceptance_criteria'],
                capabilities_needed=row['capabilities_needed'],
                team_plan=row['team_plan'],
                execution_plan=row['execution_plan'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                schema_version=row['schema_version']
            )
    
    async def update(self, project: Project) -> Project:
        """Update an existing project"""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                UPDATE projects SET
                    name = $2,
                    description = $3,
                    goal_text = $4,
                    status = $5,
                    owner_id = $6,
                    requirements = $7,
                    constraints = $8,
                    assumptions = $9,
                    acceptance_criteria = $10,
                    capabilities_needed = $11,
                    team_plan = $12,
                    execution_plan = $13,
                    updated_at = $14,
                    schema_version = $15
                WHERE id = $1
            """,
                project.id,
                project.name,
                project.description,
                project.goal.text,
                project.status.value,
                project.owner_id,
                project.requirements,
                project.constraints,
                project.assumptions,
                project.acceptance_criteria,
                project.capabilities_needed,
                project.team_plan,
                project.execution_plan,
                project.updated_at,
                project.schema_version
            )
            
        return project
    
    async def delete(self, id: UUID) -> bool:
        """Delete a project by ID"""
        async with self._pool.acquire() as conn:
            result = await conn.execute("DELETE FROM projects WHERE id = $1", id)
            return result != "DELETE 0"
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[Project]:
        """List projects with pagination"""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    id, name, description, goal_text, status, owner_id,
                    requirements, constraints, assumptions, acceptance_criteria,
                    capabilities_needed, team_plan, execution_plan,
                    created_at, updated_at, schema_version
                FROM projects ORDER BY created_at DESC LIMIT $1 OFFSET $2
            """, limit, offset)
            
            return [
                Project(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    goal=ProjectGoal(text=row['goal_text']),
                    status=row['status'],
                    owner_id=row['owner_id'],
                    requirements=row['requirements'],
                    constraints=row['constraints'],
                    assumptions=row['assumptions'],
                    acceptance_criteria=row['acceptance_criteria'],
                    capabilities_needed=row['capabilities_needed'],
                    team_plan=row['team_plan'],
                    execution_plan=row['execution_plan'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    schema_version=row['schema_version']
                ) for row in rows
            ]
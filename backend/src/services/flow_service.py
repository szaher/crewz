"""Flow service for visual workflow management."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models import Flow
from ..schemas.flows import FlowCreate, FlowUpdate, FlowResponse, FlowListResponse
from .flow_validator import FlowValidator


class FlowService:
    """Service for flow CRUD operations and validation."""

    def __init__(self, db: Session):
        self.db = db
        self.validator = FlowValidator()

    async def create_flow(self, data: FlowCreate) -> Flow:
        """
        Create a new flow.

        Args:
            data: Flow creation data

        Returns:
            Created Flow model

        Raises:
            HTTPException: If validation fails
        """
        # Only validate if flow has nodes (allow empty drafts)
        if data.nodes:
            validation_result = self.validator.validate_flow(
                nodes=data.nodes, edges=data.edges
            )

            if not validation_result["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid flow: {validation_result['errors']}",
                )

        # Convert Pydantic models to dicts for JSON storage
        nodes_dict = [node.dict() for node in data.nodes]
        edges_dict = [edge.dict() for edge in data.edges]

        flow = Flow(
            name=data.name,
            description=data.description,
            status="draft",
            nodes=nodes_dict,
            edges=edges_dict,
            version=1,
            tags=data.tags,
        )

        self.db.add(flow)
        self.db.commit()
        self.db.refresh(flow)

        return flow

    async def get_flow(self, flow_id: int) -> Flow:
        """
        Get flow by ID.

        Args:
            flow_id: Flow ID

        Returns:
            Flow model

        Raises:
            HTTPException: If flow not found
        """
        flow = self.db.query(Flow).filter(Flow.id == flow_id).first()

        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow not found",
            )

        return flow

    async def list_flows(
        self,
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> FlowListResponse:
        """
        List flows with pagination and filtering.

        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            status: Filter by status
            tags: Filter by tags (any match)

        Returns:
            FlowListResponse with flows and pagination info
        """
        query = self.db.query(Flow)

        # Apply filters
        if status:
            query = query.filter(Flow.status == status)
        else:
            # By default, exclude archived flows
            query = query.filter(Flow.status != "archived")

        if tags:
            # Filter flows that have any of the specified tags
            from sqlalchemy import func
            query = query.filter(
                func.jsonb_exists_any(Flow.tags, tags)
            )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        flows = query.offset(offset).limit(page_size).all()

        return FlowListResponse(
            flows=[FlowResponse.from_orm(f) for f in flows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update_flow(self, flow_id: int, data: FlowUpdate) -> Flow:
        """
        Update an existing flow.

        Args:
            flow_id: Flow ID
            data: Flow update data

        Returns:
            Updated Flow model

        Raises:
            HTTPException: If flow not found or validation fails
        """
        flow = await self.get_flow(flow_id)

        # Update fields
        if data.name is not None:
            flow.name = data.name

        if data.description is not None:
            flow.description = data.description

        if data.status is not None:
            flow.status = data.status

        if data.tags is not None:
            flow.tags = data.tags

        # Update nodes and edges if provided
        if data.nodes is not None and data.edges is not None:
            # Validate updated flow
            validation_result = self.validator.validate_flow(
                nodes=data.nodes, edges=data.edges
            )

            if not validation_result["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid flow: {validation_result['errors']}",
                )

            flow.nodes = [node.dict() for node in data.nodes]
            flow.edges = [edge.dict() for edge in data.edges]
            flow.version += 1

        self.db.commit()
        self.db.refresh(flow)

        return flow

    async def delete_flow(self, flow_id: int) -> None:
        """
        Delete a flow (soft delete by setting status to archived).

        Args:
            flow_id: Flow ID

        Raises:
            HTTPException: If flow not found
        """
        flow = await self.get_flow(flow_id)
        flow.status = "archived"
        self.db.commit()

    async def check_can_execute(self, flow_id: int) -> bool:
        """
        Check if a flow can be executed.

        Args:
            flow_id: Flow ID

        Returns:
            True if executable, False otherwise

        Raises:
            HTTPException: If flow cannot be executed
        """
        flow = await self.get_flow(flow_id)

        if flow.status == "archived":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot execute archived flow",
            )

        # Validate flow is executable (has proper start/end nodes)
        validation_result = self.validator.validate_executable(flow.nodes, flow.edges)

        if not validation_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Flow not executable: {validation_result['errors']}",
            )

        return True

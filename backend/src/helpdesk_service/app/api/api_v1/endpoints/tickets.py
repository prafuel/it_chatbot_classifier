"""
Ticket API endpoints.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.models import StatusEnum, PriorityEnum, SourceEnum, RoleEnum, User, Category, SubCategory, ApprovalStatusEnum
from app.common.auth import get_current_user, get_it_staff_user
from app.crud import crud_ticket
from app.services import ticket_assignment, llm_service, approval_service, automation_tasks
from app import schema

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("/", response_model=schema.TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: schema.TicketCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new ticket. Automatically detects category and approval needs using AI."""
    
    cat_id = payload.category_id
    sub_cat_id = payload.sub_category_id
    
    # 1. AI Categorization if missing
    if not cat_id:
        cls_result = llm_service.classify_query(f"{payload.title}\n{payload.description}")
        if cls_result["category"]:
            cat = db.query(Category).filter(Category.name.ilike(cls_result["category"])).first()
            if cat:
                cat_id = cat.category_id
            if cls_result["sub_category"] and cat:
                sub_cat = db.query(SubCategory).filter(
                    SubCategory.category_id == cat.category_id,
                    SubCategory.name.ilike(cls_result["sub_category"])
                ).first()
                if sub_cat:
                    sub_cat_id = sub_cat.sub_category_id

    # 2. AI Approval Analysis
    analysis = llm_service.analyze_ticket(payload.title, payload.description)
    needs_approval = analysis["needs_approval"]
    approver_id = None
    approval_status = ApprovalStatusEnum.NA
    
    if needs_approval:
        approver_id = approval_service.determine_approver_id(db, analysis["approver_type"])
        approval_status = ApprovalStatusEnum.PENDING

    # 3. Create Ticket
    ticket = crud_ticket.create_ticket(
        db=db,
        title=payload.title,
        description=payload.description,
        created_by=current_user.user_id,
        priority=payload.priority,
        category_id=cat_id,
        sub_category_id=sub_cat_id,
        source=payload.source,
        needs_approval=needs_approval,
        approver_id=approver_id,
        designated_approver_type=analysis["approver_type"],
        approval_status=approval_status,
    )

    # 4. If approval needed, wait for it. If not, auto-assign.
    if needs_approval:
        # Schedule auto-approval after 1 minute (for testing)
        background_tasks.add_task(automation_tasks.auto_approve_ticket_task, str(ticket.ticket_id))
        # Status remains NOT_ASSIGNED or PENDING until approved
        ticket.status = StatusEnum.PENDING
        db.commit()
    else:
        # Attempt automatic assignment
        ticket = ticket_assignment.auto_assign_ticket(db, ticket.ticket_id)
        
    return ticket


@router.get("/", response_model=list[schema.TicketResponse])
def list_tickets(
    status_filter: Optional[StatusEnum] = Query(None, alias="status"),
    assigned_to: Optional[uuid.UUID] = None,
    created_by: Optional[uuid.UUID] = None,
    priority: Optional[PriorityEnum] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List tickets with optional filters. Users can only see their own tickets."""
    # Enforce RBAC filtering
    if current_user.role == RoleEnum.USER:
        created_by = current_user.user_id

    return crud_ticket.list_tickets(
        db, status=status_filter, assigned_to=assigned_to,
        created_by=created_by, priority=priority, skip=skip, limit=limit,
    )


@router.get("/{ticket_id}", response_model=schema.TicketResponse)
def get_ticket(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single ticket by ID."""
    ticket = crud_ticket.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Enforce RBAC
    if current_user.role == RoleEnum.USER and ticket.created_by != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this ticket")
        
    return ticket


@router.patch("/{ticket_id}/status", response_model=schema.TicketResponse)
def update_ticket_status(
    ticket_id: uuid.UUID,
    payload: schema.TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_it_staff_user),
):
    """Update ticket status. (IT Staff Only)"""
    ticket = crud_ticket.update_ticket_status(db, ticket_id, payload.status)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # When a ticket is resolved, try to reassign pending tickets
    if payload.status == StatusEnum.RESOLVED:
        ticket_assignment.reassign_pending_tickets(db)

    return ticket


@router.patch("/{ticket_id}/assign", response_model=schema.TicketResponse)
def assign_ticket(
    ticket_id: uuid.UUID,
    payload: schema.TicketAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_it_staff_user),
):
    """Manually assign a ticket to an IT agent. (IT Staff Only)"""
    ticket = crud_ticket.assign_ticket(db, ticket_id, payload.assigned_to)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.patch("/{ticket_id}/auto-assign", response_model=schema.TicketResponse)
def auto_assign_ticket(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_it_staff_user),
):
    """Automatically assign a specific ticket to the least-loaded agent. (IT Staff Only)"""
    try:
        ticket = ticket_assignment.auto_assign_ticket(db, ticket_id)
        return ticket
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{ticket_id}", response_model=schema.TicketResponse)
def update_ticket(
    ticket_id: uuid.UUID,
    payload: schema.TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_it_staff_user),
):
    """Partial update of ticket fields (title, description, priority, category). (IT Staff Only)"""
    ticket = crud_ticket.update_ticket(
        db, ticket_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        category_id=payload.category_id,
        sub_category_id=payload.sub_category_id,
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

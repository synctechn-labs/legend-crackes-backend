import math
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.customer_repo import customer_repo
from app.schemas.customer import (
    CustomerPaginatedResponse,
    CustomerDetailResponse,
    CustomerMetricsResponse
)


class CustomerService:
    def list_customers(
        self,
        db: Session,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        phone: Optional[str] = None,
        sort_by: str = "recent"
    ) -> CustomerPaginatedResponse:
        page = max(1, page)
        limit = max(1, min(100, limit))

        customers, total = customer_repo.list_customers(
            db=db,
            page=page,
            limit=limit,
            search=search,
            phone=phone,
            sort_by=sort_by
        )

        total_pages = max(1, math.ceil(total / limit)) if total > 0 else 1

        return CustomerPaginatedResponse(
            customers=customers,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )

    def get_customer_detail(self, db: Session, customer_id: int) -> CustomerDetailResponse:
        data = customer_repo.get_customer_detail(db, customer_id)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} does not exist."
            )
        return CustomerDetailResponse(**data)

    def get_customer_orders(self, db: Session, customer_id: int) -> Dict[str, Any]:
        data = customer_repo.get_customer_detail(db, customer_id)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} does not exist."
            )
        return {
            "customer_id": customer_id,
            "customer_code": data["customer"]["customer_code"],
            "orders": data["orders"],
            "total": len(data["orders"])
        }

    def get_customer_metrics(self, db: Session) -> CustomerMetricsResponse:
        metrics = customer_repo.get_customer_metrics(db)
        return CustomerMetricsResponse(**metrics)


customer_service = CustomerService()

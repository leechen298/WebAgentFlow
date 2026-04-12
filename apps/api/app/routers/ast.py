"""AST parsing endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas.ast import FullAST
from app.schemas.common import ApiResponse
from app.services.html_ast_parser import parse_html

router = APIRouter(prefix="/ast", tags=["ast"])


class ParseHtmlRequest(BaseModel):
    """Request body for HTML → Full AST parsing."""

    html: str
    """HTML string to parse (fragment or full document)."""

    iframe_html: dict[str, str] | None = None
    """Optional mapping of iframe identifiers (src URL or data-frame-id)
    to their HTML content strings."""


@router.post("/parse", response_model=ApiResponse[FullAST])
def parse_html_to_ast(payload: ParseHtmlRequest) -> ApiResponse[FullAST]:
    """Parse HTML into a Full AST.

    Accepts raw HTML and returns a faithful DOM-structure-preserving AST.
    No semantic interpretation or restructuring is performed.
    """
    result = parse_html(payload.html, iframe_html=payload.iframe_html)
    return ApiResponse(data=result)

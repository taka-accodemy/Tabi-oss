from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

from app.services.llm_bridge import llm_bridge, QueryContext, LLMResponse
from app.services.cube_service import cube_service, CubeResponse
from app.services.vanna_service import vanna_service
from app.api.deps import get_current_active_user
from app.core.security import User
import plotly.io as pio

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    """Request model for natural language query"""
    query: str
    context: Optional[Dict[str, Any]] = None
    conversation_history: List[Dict[str, Any]] = []
    llm_provider: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for query results"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    cube_query: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None
    visualization_suggestion: Optional[str] = None
    confidence: Optional[float] = None
    requires_clarification: bool = False
    clarification_question: Optional[str] = None
    error: Optional[str] = None
    sql_query: Optional[str] = None


class DirectQueryRequest(BaseModel):
    """Request model for direct Cube.js query"""
    query: Dict[str, Any]
    explain: bool = False


@router.post("/natural", response_model=QueryResponse)
async def process_natural_language_query(
    request: QueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Process natural language query and return results"""
    try:
        # Get schema context
        schema = await cube_service.get_schema()
        schema_context = {
            "measures": schema.measures,
            "dimensions": schema.dimensions,
        }
        
        # Create query context
        context = QueryContext(
            user_query=request.query,
            conversation_history=request.conversation_history,
            schema_context=schema_context,
            user_preferences=request.context
        )
        
        # Process with LLM
        llm_response = await llm_bridge.process_query(
            context, 
            provider=request.llm_provider
        )
        
        # If LLM failed or needs clarification, return early
        if llm_response.error:
            return QueryResponse(
                success=False,
                error=llm_response.error
            )
        
        if llm_response.requires_clarification:
            return QueryResponse(
                success=True,
                requires_clarification=True,
                clarification_question=llm_response.clarification_question,
                explanation=llm_response.explanation,
                confidence=llm_response.confidence
            )
        
        # Execute Cube.js query
        if llm_response.cube_query:
            cube_response = await cube_service.execute_query(llm_response.cube_query)
            
            if cube_response.error:
                return QueryResponse(
                    success=False,
                    error=f"Cube.js query failed: {cube_response.error}",
                    cube_query=llm_response.cube_query
                )
            
            # Get SQL query for debugging
            sql_query = await cube_service.get_sql_query(llm_response.cube_query)
            
            # Generate explanation if data is available
            explanation = llm_response.explanation
            if cube_response.data:
                explanation = await llm_bridge.explain_result(
                    llm_response.cube_query, 
                    {"data": cube_response.data[:10]}  # Limit data for explanation
                )
            
            return QueryResponse(
                success=True,
                data=cube_response.data,
                cube_query=llm_response.cube_query,
                explanation=explanation,
                visualization_suggestion=llm_response.visualization_suggestion,
                confidence=llm_response.confidence,
                sql_query=sql_query
            )
        
        return QueryResponse(
            success=True,
            explanation=llm_response.explanation,
            confidence=llm_response.confidence
        )
        
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        return QueryResponse(
            success=False,
            error=str(e)
        )


@router.post("/direct", response_model=QueryResponse)
async def execute_direct_query(
    request: DirectQueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Execute direct Cube.js query"""
    try:
        # Validate query
        validation = await cube_service.validate_query(request.query)
        if not validation["valid"]:
            return QueryResponse(
                success=False,
                error=f"Invalid query: {'; '.join(validation['errors'])}"
            )
        
        # Execute query
        cube_response = await cube_service.execute_query(request.query)
        
        if cube_response.error:
            return QueryResponse(
                success=False,
                error=cube_response.error,
                cube_query=request.query
            )
        
        # Get SQL query
        sql_query = await cube_service.get_sql_query(request.query)
        
        # Generate explanation if requested
        explanation = None
        if request.explain and cube_response.data:
            explanation = await llm_bridge.explain_result(
                request.query,
                {"data": cube_response.data[:10]}
            )
        
        return QueryResponse(
            success=True,
            data=cube_response.data,
            cube_query=request.query,
            explanation=explanation,
            sql_query=sql_query
        )
        
    except Exception as e:
        logger.error(f"Direct query error: {e}")
        return QueryResponse(
            success=False,
            error=str(e)
        )


@router.post("/validate")
async def validate_query(
    query: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """Validate a Cube.js query"""
    try:
        validation = await cube_service.validate_query(query)
        return validation
    except Exception as e:
        logger.error(f"Query validation error: {e}")
        return {
            "valid": False,
            "errors": [str(e)],
            "warnings": []
        }


@router.post("/dry-run")
async def dry_run_query(
    query: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """Perform a dry run of the query"""
    try:
        result = await cube_service.dry_run_query(query)
        return result
    except Exception as e:
        logger.error(f"Dry run error: {e}")
        return {"error": str(e)}


@router.post("/sql")
async def get_sql_query(
    query: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """Get the SQL query that would be executed"""
    try:
        sql = await cube_service.get_sql_query(query)
        return {"sql": sql}
    except Exception as e:
        logger.error(f"SQL generation error: {e}")
        return {"error": str(e)}


@router.get("/suggestions")
async def get_query_suggestions(
    q: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get query suggestions based on partial input"""
    try:
        suggestions = await cube_service.get_query_suggestions(q)
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        return {"suggestions": [], "error": str(e)}
@router.post("/vanna", response_model=QueryResponse)
async def process_vanna_query(
    request: QueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Process natural language query using ChatService (Hybrid: SQL + Chat)"""
    try:
        from app.services.chat_service import chat_service
        
        result = await chat_service.process_chat(request.query, request.conversation_history)
        
        if not result.get("success"):
            return QueryResponse(
                success=False,
                error=result.get("error")
            )

        return QueryResponse(
            success=True,
            data=result.get("data"),
            sql_query=result.get("sql"),
            explanation=result.get("explanation"),
            visualization_suggestion=result.get("chart"),
            confidence=0.9
        )
        
    except Exception as e:
        logger.error(f"Vanna query error: {e}")
        return QueryResponse(
            success=False,
            error=str(e)
        )

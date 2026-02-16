from typing import Dict, Any, List, Optional
import httpx
import json
import logging
from pydantic import BaseModel
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class CubeQuery(BaseModel):
    """Cube.js query model"""
    measures: List[str] = []
    dimensions: List[str] = []
    timeDimensions: List[Dict[str, Any]] = []
    filters: List[Dict[str, Any]] = []
    order: List[Dict[str, Any]] = []
    limit: Optional[int] = None
    offset: Optional[int] = None


class CubeResponse(BaseModel):
    """Cube.js response model"""
    data: List[Dict[str, Any]] = []
    query: Dict[str, Any] = {}
    annotation: Dict[str, Any] = {}
    dataSource: str = "default"
    dbType: str = "postgres"
    extDbType: str = "cubestore"
    external: bool = False
    slowQuery: bool = False
    total: Optional[int] = None
    error: Optional[str] = None


class SchemaInfo(BaseModel):
    """Schema information model"""
    cubes: List[Dict[str, Any]] = []
    measures: Dict[str, Any] = {}
    dimensions: Dict[str, Any] = {}
    segments: Dict[str, Any] = {}


class CubeService:
    """Service for interacting with Cube.js API"""
    
    def __init__(self):
        self.base_url = settings.CUBE_API_URL
        self.api_secret = settings.CUBE_API_SECRET
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Cube.js API requests"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ChatBI-Backend/1.0.0"
        }
        
        if self.api_secret:
            headers["Authorization"] = f"Bearer {self.api_secret}"
        
        return headers
    
    async def execute_query(self, query: Dict[str, Any]) -> CubeResponse:
        """Execute a Cube.js query"""
        try:
            url = f"{self.base_url}/cubejs-api/v1/load"
            headers = self._get_headers()
            
            # Add query parameter
            params = {"query": json.dumps(query)}
            
            logger.info(f"Executing Cube.js query: {query}")
            
            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data:
                logger.error(f"Cube.js query error: {data['error']}")
                return CubeResponse(error=data["error"])
            
            return CubeResponse(**data)
            
        except httpx.TimeoutException:
            logger.error("Cube.js query timeout")
            return CubeResponse(error="Query timeout")
        except httpx.HTTPError as e:
            logger.error(f"Cube.js HTTP error: {e}")
            return CubeResponse(error=f"HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Cube.js query error: {e}")
            return CubeResponse(error=str(e))
    
    async def get_schema(self) -> SchemaInfo:
        """Get Cube.js schema information"""
        try:
            url = f"{self.base_url}/cubejs-api/v1/meta"
            headers = self._get_headers()
            
            logger.info("Fetching Cube.js schema")
            
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse schema data
            cubes = data.get("cubes", [])
            measures = {}
            dimensions = {}
            segments = {}
            
            for cube in cubes:
                cube_name = cube.get("name", "")
                
                # Extract measures
                for measure in cube.get("measures", []):
                    m_name = measure["name"]
                    measures[m_name] = {
                        "title": measure.get("title", m_name),
                        "type": measure.get("type", "number"),
                        "description": measure.get("description", ""),
                        "cube": cube_name
                    }
                
                # Extract dimensions
                for dimension in cube.get("dimensions", []):
                    d_name = dimension["name"]
                    dimensions[d_name] = {
                        "title": dimension.get("title", d_name),
                        "type": dimension.get("type", "string"),
                        "description": dimension.get("description", ""),
                        "cube": cube_name
                    }
                
                # Extract segments
                for segment in cube.get("segments", []):
                    segments[f"{cube_name}.{segment['name']}"] = {
                        "title": segment.get("title", segment["name"]),
                        "description": segment.get("description", ""),
                        "cube": cube_name
                    }
            
            return SchemaInfo(
                cubes=cubes,
                measures=measures,
                dimensions=dimensions,
                segments=segments
            )
            
        except Exception as e:
            logger.error(f"Failed to get schema: {e}")
            return SchemaInfo()
    
    async def validate_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a Cube.js query"""
        try:
            # Basic validation
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
            # Check required fields
            if not query.get("measures") and not query.get("dimensions"):
                validation_result["valid"] = False
                validation_result["errors"].append("Query must have at least one measure or dimension")
            
            # Check time dimensions format
            time_dimensions = query.get("timeDimensions", [])
            for td in time_dimensions:
                if "dimension" not in td:
                    validation_result["valid"] = False
                    validation_result["errors"].append("Time dimension must have 'dimension' field")
                
                if "granularity" not in td:
                    validation_result["warnings"].append("Time dimension without granularity")
            
            # Check filters format
            filters = query.get("filters", [])
            for f in filters:
                if "member" not in f or "operator" not in f:
                    validation_result["valid"] = False
                    validation_result["errors"].append("Filter must have 'member' and 'operator' fields")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Query validation error: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": []
            }
    
    async def get_query_suggestions(self, partial_query: str) -> List[str]:
        """Get query suggestions based on partial input"""
        try:
            # Get schema first
            schema = await self.get_schema()
            
            suggestions = []
            
            # Add measure suggestions
            for measure_name, measure_info in schema.measures.items():
                if partial_query.lower() in measure_name.lower() or partial_query.lower() in measure_info["title"].lower():
                    suggestions.append(f"measure: {measure_name} ({measure_info['title']})")
            
            # Add dimension suggestions
            for dim_name, dim_info in schema.dimensions.items():
                if partial_query.lower() in dim_name.lower() or partial_query.lower() in dim_info["title"].lower():
                    suggestions.append(f"dimension: {dim_name} ({dim_info['title']})")
            
            return suggestions[:10]  # Return top 10 suggestions
            
        except Exception as e:
            logger.error(f"Failed to get suggestions: {e}")
            return []
    
    async def dry_run_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a dry run of the query (validation only)"""
        try:
            url = f"{self.base_url}/cubejs-api/v1/dry-run"
            headers = self._get_headers()
            
            params = {"query": json.dumps(query)}
            
            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Dry run error: {e}")
            return {"error": str(e)}
    
    async def get_sql_query(self, query: Dict[str, Any]) -> str:
        """Get the SQL query that would be executed"""
        try:
            url = f"{self.base_url}/cubejs-api/v1/sql"
            headers = self._get_headers()
            
            params = {"query": json.dumps(query)}
            
            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get("sql", "")
            
        except Exception as e:
            logger.error(f"Failed to get SQL: {e}")
            return ""
    
    async def health_check(self) -> bool:
        """Check if Cube.js is healthy"""
        try:
            url = f"{self.base_url}/livez"
            response = await self.client.get(url, timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Cube.js health check failed: {e}")
            return False


# Global instance
cube_service = CubeService()
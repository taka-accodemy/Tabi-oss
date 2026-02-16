from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

from app.services.cube_service import cube_service
from app.services.vanna_service import vanna_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def get_schema():
    """Get complete schema information"""
    try:
        schema = await cube_service.get_schema()
        return {
            "cubes": schema.cubes,
            "measures": schema.measures,
            "dimensions": schema.dimensions,
            "segments": schema.segments
        }
    except Exception as e:
        logger.error(f"Schema retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/measures")
async def get_measures():
    """Get all available measures"""
    try:
        schema = await cube_service.get_schema()
        return {"measures": schema.measures}
    except Exception as e:
        logger.error(f"Measures retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dimensions")
async def get_dimensions():
    """Get all available dimensions"""
    try:
        schema = await cube_service.get_schema()
        return {"dimensions": schema.dimensions}
    except Exception as e:
        logger.error(f"Dimensions retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cubes")
async def get_cubes():
    """Get all available cubes"""
    try:
        schema = await cube_service.get_schema()
        return {"cubes": schema.cubes}
    except Exception as e:
        logger.error(f"Cubes retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cubes/{cube_name}")
async def get_cube_details(cube_name: str):
    """Get details for a specific cube"""
    try:
        schema = await cube_service.get_schema()
        
        # Find the cube
        cube = None
        for c in schema.cubes:
            if c.get("name") == cube_name:
                cube = c
                break
        
        if not cube:
            raise HTTPException(status_code=404, detail=f"Cube '{cube_name}' not found")
        
        return {"cube": cube}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cube details retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_schema(q: str):
    """Search schema elements by name or title"""
    try:
        schema = await cube_service.get_schema()
        query = q.lower()
        
        results = {
            "measures": [],
            "dimensions": [],
            "cubes": []
        }
        
        # Search measures
        for measure_name, measure_info in schema.measures.items():
            if (query in measure_name.lower() or 
                query in measure_info.get("title", "").lower() or
                query in measure_info.get("description", "").lower()):
                results["measures"].append({
                    "name": measure_name,
                    "info": measure_info
                })
        
        # Search dimensions
        for dim_name, dim_info in schema.dimensions.items():
            if (query in dim_name.lower() or 
                query in dim_info.get("title", "").lower() or
                query in dim_info.get("description", "").lower()):
                results["dimensions"].append({
                    "name": dim_name,
                    "info": dim_info
                })
        
        # Search cubes
        for cube in schema.cubes:
            cube_name = cube.get("name", "")
            cube_title = cube.get("title", "")
            cube_description = cube.get("description", "")
            
            if (query in cube_name.lower() or 
                query in cube_title.lower() or
                query in cube_description.lower()):
                results["cubes"].append(cube)
        
        return results
    except Exception as e:
        logger.error(f"Schema search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training")
async def get_training_data():
    """Get all training data from Vanna"""
    try:
        data = vanna_service.get_training_data()
        return {"data": data}
    except Exception as e:
        logger.error(f"Error getting training data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata")
async def get_semantic_metadata():
    """Get persistent semantic metadata (descriptions, polarity)"""
    from app.services.semantic_metadata_service import semantic_metadata_service
    return semantic_metadata_service.get_all()


class MetadataItem(BaseModel):
    name: str
    type: str
    description: str
    polarity: str = "neutral"


class MetadataUpdateRequest(BaseModel):
    metadata: List[MetadataItem]


@router.post("/metadata")
async def update_semantic_metadata(request: MetadataUpdateRequest):
    """Update persistent semantic metadata and trigger Vanna training"""
    from app.services.semantic_metadata_service import semantic_metadata_service
    try:
        items = [item.dict() for item in request.metadata]
        # 1. Save to persistent storage (JSON)
        semantic_metadata_service.update_items(items)
        
        # 2. Clear existing documentation training from Vanna (OSS Strategy: keep clean)
        vanna_service.clear_documentation_training()
        
        # 3. Train Vanna with the current full state (Hybrid: Vanna is brain, JSON is source of truth)
        success = vanna_service.train_structured_metadata(items)
        
        if not success:
             logger.warning("Vanna training failed, but metadata was saved to JSON.")
             
        return {"success": True, "message": "Metadata updated and AI trained"}
    except Exception as e:
        logger.error(f"Error updating metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TrainRequest(BaseModel):
    documentation: Optional[str] = None
    metadata: Optional[List[Dict[str, Any]]] = None


@router.post("/train")
async def train_metadata(request: TrainRequest):
    """Train Vanna with documentation or structured metadata"""
    try:
        if request.metadata:
            success = vanna_service.train_structured_metadata(request.metadata)
        elif request.documentation:
            success = vanna_service.train_documentation(request.documentation)
        else:
            raise HTTPException(status_code=400, detail="Either 'documentation' or 'metadata' is required")
            
        if not success:
            raise HTTPException(status_code=500, detail="Failed to train Vanna")
        return {"success": True, "message": "Successfully updated AI context"}
    except Exception as e:
        logger.error(f"Error training: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/training/{training_id}")
async def remove_training_data(training_id: str):
    """Remove specific training data"""
    try:
        success = vanna_service.remove_training_data(training_id)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to remove training data {training_id}")
        return {"success": True, "message": f"Successfully removed training data {training_id}"}
    except Exception as e:
        logger.error(f"Error removing training data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/training/all/everything")
async def clear_all_training_data():
    """Clear all training data from Vanna"""
    try:
        success = vanna_service.clear_all_training_data()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to clear all training data")
        return {"success": True, "message": "Successfully cleared all training data"}
    except Exception as e:
        logger.error(f"Error clearing all training data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
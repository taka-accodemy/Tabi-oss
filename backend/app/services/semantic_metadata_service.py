import json
import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class SemanticMetadataService:
    def __init__(self):
        # Path to storage file
        self.storage_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/semantic_metadata.json"))
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from JSON file"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading semantic metadata: {e}")
                return {}
        return {}

    def _save_metadata(self) -> bool:
        """Save metadata to JSON file"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving semantic metadata: {e}")
            return False

    def get_all(self) -> Dict[str, Any]:
        """Get all metadata"""
        return self.metadata

    def get_item(self, name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific item"""
        return self.metadata.get(name)

    def update_items(self, items: List[Dict[str, Any]]) -> bool:
        """Update multiple metadata items"""
        for item in items:
            name = item.get("name")
            if not name:
                continue
            
            # Preserve existing if not provided
            existing = self.metadata.get(name, {})
            self.metadata[name] = {
                "name": name,
                "type": item.get("type", existing.get("type", "measure")),
                "description": item.get("description", existing.get("description", "")),
                "polarity": item.get("polarity", existing.get("polarity", "neutral")), # positive, negative, neutral
                "last_updated": item.get("last_updated")
            }
        
        return self._save_metadata()

semantic_metadata_service = SemanticMetadataService()

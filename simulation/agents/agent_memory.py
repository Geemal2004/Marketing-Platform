"""
Agent memory system using ChromaDB for vector storage
"""
import logging
import time
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class AgentMemoryStore:
    """
    Vector database for storing and retrieving agent memories
    
    Uses ChromaDB for:
    - Agent profile embeddings
    - Past experiences and interactions
    - RAG (Retrieval Augmented Generation) context for decisions
    """
    
    def __init__(
        self,
        chroma_host: str = "localhost",
        chroma_port: int = 8000,
        collection_name: str = "agent_memories"
    ):
        """
        Initialize connection to ChromaDB
        
        Args:
            chroma_host: ChromaDB server host
            chroma_port: ChromaDB server port
            collection_name: Name of the collection to use
        """
        try:
            self.client = chromadb.HttpClient(
                host=chroma_host,
                port=chroma_port
            )
            
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Agent profiles and interaction history"}
            )
            
            logger.info(f"Connected to ChromaDB at {chroma_host}:{chroma_port}")
            
        except Exception as e:
            logger.warning(f"Could not connect to ChromaDB: {e}. Using in-memory storage.")
            # Fallback to in-memory
            self.client = chromadb.Client()
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Agent profiles and interaction history"}
            )
    
    def create_agent_profile(self, agent_id: str, profile: Dict[str, Any]):
        """
        Store agent's demographic profile and values
        
        Args:
            agent_id: Unique agent identifier
            profile: Agent profile dict with demographics and values
        """
        # Convert profile to text for embedding
        values = profile.get('values', [])
        values_str = ', '.join(values) if values else 'Not specified'
        
        profile_text = f"""
Demographics:
- Age: {profile.get('age', 'Unknown')}
- Gender: {profile.get('gender', 'Unknown')}
- Location: {profile.get('location', 'Unknown')}
- Education: {profile.get('education', 'Not specified')}
- Occupation: {profile.get('occupation', 'Not specified')}

Core values: {values_str}
"""
        
        try:
            # Check if profile already exists
            existing = self.collection.get(ids=[f"{agent_id}_profile"])
            if existing['ids']:
                # Update existing
                self.collection.update(
                    ids=[f"{agent_id}_profile"],
                    documents=[profile_text],
                    metadatas=[{"agent_id": agent_id, "type": "profile", **profile}]
                )
            else:
                # Add new
                self.collection.add(
                    ids=[f"{agent_id}_profile"],
                    documents=[profile_text],
                    metadatas=[{"agent_id": agent_id, "type": "profile", **profile}]
                )
            
            logger.debug(f"Stored profile for agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to store profile for {agent_id}: {e}")
    
    def add_experience(
        self,
        agent_id: str,
        experience: str,
        experience_type: str = "interaction"
    ):
        """
        Store a past interaction or experience
        
        Args:
            agent_id: Agent identifier
            experience: Description of the experience
            experience_type: Type of experience (interaction, boycott, endorsement)
        """
        experience_id = f"{agent_id}_exp_{int(time.time() * 1000)}"
        
        try:
            self.collection.add(
                ids=[experience_id],
                documents=[experience],
                metadatas=[{
                    "agent_id": agent_id,
                    "type": experience_type,
                    "timestamp": time.time()
                }]
            )
            logger.debug(f"Added experience for {agent_id}: {experience[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to add experience for {agent_id}: {e}")
    
    def query_relevant_context(
        self,
        agent_id: str,
        query: str,
        n_results: int = 3
    ) -> List[str]:
        """
        Retrieve relevant memories for decision-making (RAG)
        
        Args:
            agent_id: Agent to query memories for
            query: Query text (e.g., ad content to react to)
            n_results: Number of results to return
        
        Returns:
            List of relevant memory documents
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                where={"agent_id": agent_id},
                n_results=n_results
            )
            
            if results and results['documents']:
                return results['documents'][0]
            return []
            
        except Exception as e:
            logger.error(f"Failed to query memories for {agent_id}: {e}")
            return []
    
    def get_agent_profile(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get stored profile for an agent"""
        try:
            results = self.collection.get(
                ids=[f"{agent_id}_profile"],
                include=["metadatas"]
            )
            
            if results and results['metadatas']:
                return results['metadatas'][0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get profile for {agent_id}: {e}")
            return None
    
    def clear_agent_memories(self, agent_id: str):
        """Remove all memories for an agent"""
        try:
            # Get all IDs for this agent
            results = self.collection.get(
                where={"agent_id": agent_id},
                include=["metadatas"]
            )
            
            if results and results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Cleared {len(results['ids'])} memories for {agent_id}")
                
        except Exception as e:
            logger.error(f"Failed to clear memories for {agent_id}: {e}")
    
    def clear_all(self):
        """Clear entire collection (use with caution)"""
        try:
            # Delete and recreate collection
            self.client.delete_collection(self.collection.name)
            self.collection = self.client.create_collection(
                name=self.collection.name,
                metadata={"description": "Agent profiles and interaction history"}
            )
            logger.info("Cleared all agent memories")
            
        except Exception as e:
            logger.error(f"Failed to clear all memories: {e}")

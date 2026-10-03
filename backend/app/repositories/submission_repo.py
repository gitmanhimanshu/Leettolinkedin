"""Repository for storing and retrieving submissions, with MongoDB and in-memory fallback support."""

import logging
from typing import Optional, List, Dict
from datetime import datetime, timezone
from backend.app.models.submission import SubmissionModel
from backend.app.config import settings

logger = logging.getLogger(__name__)


class SubmissionRepository:
    """Repository handling persistence for LeetCode submissions with idempotency guarantees."""

    def __init__(self):
        self._in_memory_db: Dict[str, SubmissionModel] = {}
        self._mongo_client = None
        self._collection = None
        self._init_mongo()

    def _init_mongo(self):
        """Attempt to initialize MongoDB client; gracefully fallback to in-memory store if unavailable."""
        try:
            import pymongo
            client = pymongo.MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=1000,
            )
            # Ping database to check reachability
            client.admin.command('ping')
            db = client[settings.MONGODB_DB_NAME]
            self._collection = db["submissions"]
            # Ensure index on submission_id
            self._collection.create_index("submission_id", unique=True)
            self._mongo_client = client
            logger.info("Connected to MongoDB at %s", settings.MONGODB_URI)
        except Exception as e:
            logger.warning(
                "MongoDB not reachable (%s). Using thread-safe in-memory store for Phase 1/2 development.",
                str(e)
            )
            self._collection = None

    def get_by_id(self, submission_id: str) -> Optional[SubmissionModel]:
        """Retrieve submission by its unique submission ID."""
        if self._collection is not None:
            try:
                doc = self._collection.find_one({"submission_id": submission_id})
                if doc:
                    return SubmissionModel.from_dict(doc)
            except Exception as e:
                logger.error("MongoDB query error: %s", e)

        return self._in_memory_db.get(submission_id)

    def save(self, submission: SubmissionModel) -> SubmissionModel:
        """Upsert a submission using submission_id as idempotency key."""
        submission.updated_at = datetime.now(timezone.utc)

        # Always update memory cache
        self._in_memory_db[submission.submission_id] = submission

        if self._collection is not None:
            try:
                self._collection.update_one(
                    {"submission_id": submission.submission_id},
                    {"$set": submission.to_dict()},
                    upsert=True
                )
            except Exception as e:
                logger.error("MongoDB save error: %s", e)

        return submission

    def list_all(self, limit: int = 50) -> List[SubmissionModel]:
        """List recent submissions ordered by creation timestamp."""
        if self._collection is not None:
            try:
                cursor = self._collection.find().sort("created_at", -1).limit(limit)
                return [SubmissionModel.from_dict(doc) for doc in cursor]
            except Exception as e:
                logger.error("MongoDB list error: %s", e)

        items = list(self._in_memory_db.values())
        items.sort(key=lambda s: s.created_at, reverse=True)
        return items[:limit]

    def clear(self):
        """Clear store (primarily for unit testing)."""
        self._in_memory_db.clear()
        if self._collection is not None:
            try:
                self._collection.delete_many({})
            except Exception as e:
                logger.error("MongoDB clear error: %s", e)


submission_repo = SubmissionRepository()

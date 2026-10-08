"""Repository for storing and retrieving submissions, with MongoDB and in-memory fallback support."""

import logging
from typing import Optional, List, Dict, Any
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

    def save_auth(self, service: str, data: Dict[str, Any]):
        """Persist authentication tokens across serverless invocations."""
        import json
        import os
        import tempfile

        # 1. Save to MongoDB if available
        if self._mongo_client is not None:
            try:
                db = self._mongo_client[settings.MONGODB_DB_NAME]
                db["auth"].update_one(
                    {"service": service},
                    {"$set": {"service": service, "data": data, "updated_at": datetime.now(timezone.utc)}},
                    upsert=True
                )
            except Exception as e:
                logger.warning("MongoDB auth save error: %s", e)

        # 2. Save to local/serverless temp file
        try:
            temp_path = os.path.join(tempfile.gettempdir(), f"c2l_auth_{service}.json")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning("Temp file auth save error: %s", e)

    def get_auth(self, service: str) -> Optional[Dict[str, Any]]:
        """Retrieve persisted authentication tokens."""
        import json
        import os
        import tempfile

        # 1. Try MongoDB first
        if self._mongo_client is not None:
            try:
                db = self._mongo_client[settings.MONGODB_DB_NAME]
                doc = db["auth"].find_one({"service": service})
                if doc and "data" in doc:
                    return doc["data"]
            except Exception as e:
                logger.warning("MongoDB auth read error: %s", e)

        # 2. Fallback to temp file
        try:
            temp_path = os.path.join(tempfile.gettempdir(), f"c2l_auth_{service}.json")
            if os.path.exists(temp_path):
                with open(temp_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning("Temp file auth read error: %s", e)

        return None

    def clear(self):
        """Clear store (primarily for unit testing)."""
        self._in_memory_db.clear()
        if self._collection is not None:
            try:
                self._collection.delete_many({})
            except Exception as e:
                logger.error("MongoDB clear error: %s", e)


submission_repo = SubmissionRepository()


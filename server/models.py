from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from server.db import Base
from datetime import datetime, timezone
import uuid


class LogEntry(Base):
    __tablename__ = "log_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    session_id = Column(String(255), index=True, nullable=True)
    user_id = Column(String(255), index=True, nullable=True)
    app_name = Column(String(255), index=True, nullable=True)
    provider = Column(String(50), index=True)
    model = Column(String(100), index=True)
    prompt = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=True)
    cost_usd = Column(Float, nullable=True)
    tags = Column(JSON, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    error = Column(Text, nullable=True)

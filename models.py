from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(String)
    priority: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Escalation(Base):
    __tablename__ = "escalations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"))
    reason: Mapped[str] = mapped_column(String)
    escalated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_by: Mapped[str | None] = mapped_column(String, nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ticket_id: Mapped[str | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    severity: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    trace_id: Mapped[str] = mapped_column(String)
    event_type: Mapped[str] = mapped_column(String)
    risk_flags: Mapped[str] = mapped_column(String)
    action_taken: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class KnowledgeArticle(Base):
    __tablename__ = "knowledge_articles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(String)
    source_ticket_id: Mapped[str | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class AgentTrace(Base):
    __tablename__ = "agent_traces"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    trace_id: Mapped[str] = mapped_column(String)
    agent_name: Mapped[str] = mapped_column(String)
    input_summary: Mapped[str] = mapped_column(String)
    output_summary: Mapped[str] = mapped_column(String)
    duration_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
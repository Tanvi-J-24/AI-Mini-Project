from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Algorithm = Literal["astar", "bfs", "greedy"]
Severity = Literal["critical", "high", "medium", "low"]


class RouteRequest(BaseModel):
    source: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    algorithm: Algorithm = "astar"
    risk_weight: float = Field(0.0, ge=0, le=20)
    incident_id: Optional[str] = None
    station_id: Optional[str] = None


class CompareRequest(BaseModel):
    source: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    risk_weight: float = Field(0.0, ge=0, le=20)
    repeats: int = Field(25, ge=1, le=200, description="Timing repetitions (median reported)")


class RiskCompareRequest(BaseModel):
    source: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    risk_weight: float = Field(3.0, ge=0, le=20)


class EdgeRequest(BaseModel):
    u: str = Field(min_length=1)
    v: str = Field(min_length=1)


class IncidentCreate(BaseModel):
    node: Optional[str] = None
    type: Optional[str] = Field(None, max_length=60)
    severity: Optional[Severity] = None
    people_affected: Optional[int] = Field(None, ge=0, le=10000)
    description: Optional[str] = Field(None, max_length=200)


class ResolveRequest(BaseModel):
    incident_id: str = Field(min_length=1)


class ReplanRequest(BaseModel):
    source: Optional[str] = None
    destination: Optional[str] = None
    algorithm: Optional[Algorithm] = None
    risk_weight: Optional[float] = Field(None, ge=0, le=20)


class ResetRequest(BaseModel):
    clear_metrics: bool = False


class LoadScenarioRequest(BaseModel):
    clear_metrics: bool = False


class RouteResult(BaseModel):
    algorithm: str
    algorithm_label: str
    source: str
    destination: str
    success: bool
    path: list[str]
    path_edges: list[str]
    cost: float
    travel_cost: float
    risk_total: float
    risk_weight: float
    segments: int
    nodes_explored: int
    explored: list[str]
    execution_time_ms: float
    estimated_minutes: Optional[float]
    message: str


class MutationResponse(BaseModel):
    ok: bool = True
    message: str
    state: dict[str, Any]
    route: Optional[dict[str, Any]] = None
    replan: Optional[dict[str, Any]] = None
    extra: Optional[dict[str, Any]] = None


class ComparisonResponse(BaseModel):
    source: str
    destination: str
    risk_weight: float
    repeats: int
    optimal_cost: Optional[float]
    results: list[dict[str, Any]]
    notes: list[str]
    state: dict[str, Any]

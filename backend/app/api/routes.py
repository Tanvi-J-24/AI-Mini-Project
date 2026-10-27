from __future__ import annotations

from fastapi import APIRouter

from ..models.schemas import (CompareRequest, ComparisonResponse, EdgeRequest, IncidentCreate,
                              LoadScenarioRequest, MutationResponse, ReplanRequest, ResetRequest,
                              ResolveRequest, RiskCompareRequest, RouteRequest)
from ..services.simulation_service import simulation as sim

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "RescueRoute AI", "scenario": sim.scenario.id}


@router.get("/scenarios")
def list_scenarios() -> dict:
    return {"scenarios": sim.list_scenarios(), "current": sim.scenario.id}


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str) -> dict:
    return sim.scenario_definition(scenario_id)


@router.post("/scenarios/{scenario_id}/load", response_model=MutationResponse)
def load_scenario(scenario_id: str, body: LoadScenarioRequest | None = None) -> MutationResponse:
    msg = sim.load_scenario(scenario_id, clear_metrics=bool(body and body.clear_metrics))
    return MutationResponse(message=msg, state=sim.state())


@router.get("/state")
def get_state() -> dict:
    return sim.state()


@router.post("/route", response_model=MutationResponse)
def route(req: RouteRequest) -> MutationResponse:
    res = sim.route(req.source, req.destination, req.algorithm, req.risk_weight,
                    req.incident_id, req.station_id)
    msg = "Route calculated" if res["success"] else "No safe route available"
    return MutationResponse(ok=res["success"], message=msg, route=res, state=sim.state())


@router.post("/compare", response_model=ComparisonResponse)
def compare(req: CompareRequest) -> ComparisonResponse:
    out = sim.compare(req.source, req.destination, req.risk_weight, req.repeats)
    notes = [
        "BFS minimises the number of segments, not total cost.",
        "Greedy Best-First follows the heuristic only and is not guaranteed optimal.",
        "A* is optimal here because the heuristic is admissible for the edge-cost model.",
        "Execution time is the median of repeated runs; on very small graphs it is dominated by measurement noise.",
    ]
    return ComparisonResponse(source=req.source, destination=req.destination,
                              risk_weight=req.risk_weight, repeats=req.repeats,
                              optimal_cost=out["optimal_cost"], results=out["results"],
                              notes=notes, state=sim.state())


@router.post("/risk-compare", response_model=MutationResponse)
def risk_compare(req: RiskCompareRequest) -> MutationResponse:
    out = sim.risk_compare(req.source, req.destination, req.risk_weight)
    return MutationResponse(message="Risk comparison complete", extra=out, state=sim.state())


@router.post("/block-road", response_model=MutationResponse)
def block_road(req: EdgeRequest) -> MutationResponse:
    msg, replan = sim.block_road(req.u, req.v)
    st = sim.state()
    return MutationResponse(message=msg, replan=replan, route=st["active_route"], state=st)


@router.post("/unblock-road", response_model=MutationResponse)
def unblock_road(req: EdgeRequest) -> MutationResponse:
    msg, replan = sim.unblock_road(req.u, req.v)
    st = sim.state()
    return MutationResponse(message=msg, replan=replan, route=st["active_route"], state=st)


@router.post("/incidents", response_model=MutationResponse, status_code=201)
def add_incident(req: IncidentCreate | None = None) -> MutationResponse:
    data = req.model_dump() if req else {}
    inc = sim.add_incident(**data)
    return MutationResponse(message=f"Incident {inc['id']} added", extra={"incident": inc},
                            state=sim.state())


@router.post("/resolve-incident", response_model=MutationResponse)
def resolve_incident(req: ResolveRequest) -> MutationResponse:
    msg = sim.resolve_incident(req.incident_id)
    return MutationResponse(message=msg, state=sim.state())


@router.post("/replan", response_model=MutationResponse)
def replan(req: ReplanRequest | None = None) -> MutationResponse:
    req = req or ReplanRequest()
    res, info = sim.replan(req.source, req.destination, req.algorithm, req.risk_weight)
    msg = "Route recalculated" if res["success"] else "No safe route available"
    return MutationResponse(ok=res["success"], message=msg, route=res, replan=info, state=sim.state())


@router.post("/reset", response_model=MutationResponse)
def reset(req: ResetRequest | None = None) -> MutationResponse:
    msg = sim.reset(clear_metrics=bool(req and req.clear_metrics))
    return MutationResponse(message=msg, state=sim.state())


@router.post("/demo", response_model=MutationResponse)
def demo() -> MutationResponse:
    out = sim.run_demo()
    return MutationResponse(message="Multi-incident demo complete", extra=out, state=sim.state())

"""
Metrics API Routes

Exposes agent performance metrics and health data via REST endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import logging

from ...agents.agent_metrics import AgentMetrics

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
    responses={404: {"description": "Not found"}},
)

# Global metrics instance (In a real app, this might be injected via dependency)
# For now, we assume it's managed by the main application state
_metrics_instance: Optional[AgentMetrics] = None

def get_metrics() -> AgentMetrics:
    """Dependency to get the metrics instance"""
    global _metrics_instance
    if _metrics_instance is None:
        # In production, this should be initialized elsewhere and injected
        _metrics_instance = AgentMetrics()
    return _metrics_instance

@router.get("/summary")
async def get_dashboard_summary(metrics: AgentMetrics = Depends(get_metrics)) -> Dict[str, Any]:
    """
    Get a comprehensive dashboard summary of agent performance.
    
    Returns:
        JSON object containing plan, step, tool, and autonomy metrics.
    """
    try:
        return metrics.get_dashboard_summary()
    except Exception as e:
        logger.error(f"Error retrieving dashboard summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving metrics")

@router.get("/plans")
async def get_plan_metrics(metrics: AgentMetrics = Depends(get_metrics)) -> Dict[str, Any]:
    """Get metrics related specifically to plan execution."""
    return metrics.get_plan_metrics()

@router.get("/steps")
async def get_step_metrics(metrics: AgentMetrics = Depends(get_metrics)) -> Dict[str, Any]:
    """Get metrics related to individual step executions."""
    return metrics.get_step_metrics()

@router.get("/tools")
async def get_tool_metrics(
    tool_name: Optional[str] = None,
    metrics: AgentMetrics = Depends(get_metrics)
) -> Dict[str, Any]:
    """
    Get metrics for all tools or a specific tool.
    
    Args:
        tool_name: Optional name of the tool to filter by.
    """
    return metrics.get_tool_metrics(tool_name)

@router.get("/autonomy")
async def get_autonomy_metrics(metrics: AgentMetrics = Depends(get_metrics)) -> Dict[str, Any]:
    """Get metrics related to agent autonomy and user trust."""
    return metrics.get_autonomy_metrics()

@router.get("/latency")
async def get_latency_metrics(metrics: AgentMetrics = Depends(get_metrics)) -> Dict[str, Any]:
    """Get execution latency percentiles and averages."""
    return metrics.get_latency_metrics()

@router.get("/export")
async def export_all_metrics(metrics: AgentMetrics = Depends(get_metrics)) -> Dict[str, Any]:
    """Export all metrics in a single comprehensive report."""
    return metrics.export_metrics()

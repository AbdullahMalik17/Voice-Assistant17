"""
Agent Performance Metrics & Monitoring

Comprehensive observability for agent behavior, providing KPIs, health checks,
and insights into agent performance and reliability.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from .planner import Plan, PlanStatus, StepStatus

logger = logging.getLogger(__name__)


@dataclass
class MetricDataPoint:
    """A single metric data point with timestamp"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


class AgentMetrics:
    """
    Tracks agent performance metrics and KPIs.
    
    Metrics tracked:
    - Plans created, completed, failed
    - Average steps per plan
    - Step success rate
    - Confirmation acceptance rate
    - Tool failure rates by tool
    - Execution latency (p50, p95, p99)
    - Autonomy score (% auto-executed)
    """
    
    def __init__(self, retention_days: int = 7):
        """
        Initialize metrics collector.
        
        Args:
            retention_days: How long to retain historical metrics
        """
        self.retention_days = retention_days
        self.last_cleanup = datetime.now()
        
        # Counters (cumulative)
        self.plans_created = 0
        self.plans_completed = 0
        self.plans_failed = 0
        self.plans_cancelled = 0
        
        self.steps_executed = 0
        self.steps_succeeded = 0
        self.steps_failed = 0
        self.steps_skipped = 0
        
        self.confirmations_required = 0
        self.confirmations_approved = 0
        self.confirmations_rejected = 0
        
        # Tool-specific metrics
        self.tool_executions: Dict[str, int] = defaultdict(int)
        self.tool_successes: Dict[str, int] = defaultdict(int)
        self.tool_failures: Dict[str, int] = defaultdict(int)
        self.tool_latencies: Dict[str, List[float]] = defaultdict(list)
        
        # Time series data
        self.execution_times: List[MetricDataPoint] = []
        self.autonomy_scores: List[MetricDataPoint] = []
        self.success_rates: List[MetricDataPoint] = []
    
    def record_plan_created(self, plan: Plan) -> None:
        """Record a new plan creation"""
        self.plans_created += 1
    
    def record_plan_completion(self, plan: Plan) -> None:
        """Record plan completion"""
        if plan.status == PlanStatus.COMPLETED:
            self.plans_completed += 1
        elif plan.status == PlanStatus.FAILED:
            self.plans_failed += 1
        elif plan.status == PlanStatus.CANCELLED:
            self.plans_cancelled += 1
        
        # Record execution time
        if plan.started_at and plan.completed_at:
            duration = (plan.completed_at - plan.started_at).total_seconds()
            self.execution_times.append(MetricDataPoint(
                timestamp=datetime.now(),
                value=duration,
                tags={"status": plan.status.value}
            ))
    
    def record_step_execution(
        self,
        tool_name: str,
        success: bool,
        latency_seconds: float,
        requires_confirmation: bool = False,
        confirmed: Optional[bool] = None
    ) -> None:
        """
        Record a step execution.
        
        Args:
            tool_name: Name of the tool executed
            success: Whether execution succeeded
            latency_seconds: Execution time in seconds
            requires_confirmation: Whether this step required confirmation
            confirmed: Whether user confirmed (if applicable)
        """
        self.steps_executed += 1
        self.tool_executions[tool_name] += 1
        self.tool_latencies[tool_name].append(latency_seconds)
        
        if success:
            self.steps_succeeded += 1
            self.tool_successes[tool_name] += 1
        else:
            self.steps_failed += 1
            self.tool_failures[tool_name] += 1
        
        if requires_confirmation:
            self.confirmations_required += 1
            if confirmed is True:
                self.confirmations_approved += 1
            elif confirmed is False:
                self.confirmations_rejected += 1
    
    def record_step_skipped(self) -> None:
        """Record a skipped step"""
        self.steps_skipped += 1
    
    def get_plan_metrics(self) -> Dict[str, Any]:
        """Get plan-level metrics"""
        total_plans = self.plans_created
        
        return {
            "plans_created": self.plans_created,
            "plans_completed": self.plans_completed,
            "plans_failed": self.plans_failed,
            "plans_cancelled": self.plans_cancelled,
            "completion_rate": f"{(self.plans_completed / total_plans * 100):.1f}%" if total_plans > 0 else "N/A",
            "success_rate": f"{((self.plans_completed - self.plans_failed) / total_plans * 100):.1f}%" if total_plans > 0 else "N/A",
        }
    
    def get_step_metrics(self) -> Dict[str, Any]:
        """Get step-level metrics"""
        total_steps = self.steps_executed
        
        return {
            "steps_executed": self.steps_executed,
            "steps_succeeded": self.steps_succeeded,
            "steps_failed": self.steps_failed,
            "steps_skipped": self.steps_skipped,
            "success_rate": f"{(self.steps_succeeded / total_steps * 100):.1f}%" if total_steps > 0 else "N/A",
            "failure_rate": f"{(self.steps_failed / total_steps * 100):.1f}%" if total_steps > 0 else "N/A",
        }
    
    def get_tool_metrics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for a specific tool or all tools"""
        if tool_name:
            executions = self.tool_executions.get(tool_name, 0)
            successes = self.tool_successes.get(tool_name, 0)
            failures = self.tool_failures.get(tool_name, 0)
            latencies = self.tool_latencies.get(tool_name, [])
            
            return {
                "tool": tool_name,
                "executions": executions,
                "successes": successes,
                "failures": failures,
                "success_rate": f"{(successes / executions * 100):.1f}%" if executions > 0 else "N/A",
                "avg_latency_ms": f"{(sum(latencies) / len(latencies) * 1000):.1f}" if latencies else "N/A",
                "p95_latency_ms": f"{(sorted(latencies)[int(len(latencies) * 0.95)] * 1000):.1f}" if latencies else "N/A",
            }
        else:
            # All tools
            metrics = {}
            for tool in self.tool_executions.keys():
                metrics[tool] = self.get_tool_metrics(tool)
            return metrics
    
    def get_autonomy_metrics(self) -> Dict[str, Any]:
        """Get autonomy-related metrics"""
        total_confirmations = self.confirmations_approved + self.confirmations_rejected
        
        return {
            "confirmations_required": self.confirmations_required,
            "confirmations_approved": self.confirmations_approved,
            "confirmations_rejected": self.confirmations_rejected,
            "acceptance_rate": f"{(self.confirmations_approved / total_confirmations * 100):.1f}%" if total_confirmations > 0 else "N/A",
            "autonomy_score": f"{((self.steps_executed - self.confirmations_required) / max(self.steps_executed, 1) * 100):.1f}%",
        }
    
    def get_latency_metrics(self) -> Dict[str, Any]:
        """Get execution latency metrics"""
        if not self.execution_times:
            return {"status": "no_data"}
        
        times = [ep.value for ep in self.execution_times]
        sorted_times = sorted(times)
        
        return {
            "total_executions": len(times),
            "avg_latency_s": f"{(sum(times) / len(times)):.2f}",
            "min_latency_s": f"{min(times):.2f}",
            "max_latency_s": f"{max(times):.2f}",
            "p50_latency_s": f"{sorted_times[len(sorted_times)//2]:.2f}",
            "p95_latency_s": f"{sorted_times[int(len(sorted_times)*0.95)]:.2f}",
            "p99_latency_s": f"{sorted_times[int(len(sorted_times)*0.99)]:.2f}",
        }
    
    def get_top_failing_tools(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Get tools with highest failure rates"""
        tool_metrics = []
        
        for tool_name, executions in self.tool_executions.items():
            failures = self.tool_failures[tool_name]
            if executions > 0:
                failure_rate = failures / executions
                tool_metrics.append({
                    "tool": tool_name,
                    "executions": executions,
                    "failures": failures,
                    "failure_rate": f"{(failure_rate * 100):.1f}%"
                })
        
        return sorted(tool_metrics, key=lambda x: float(x["failure_rate"].rstrip('%')), reverse=True)[:top_n]
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get a comprehensive dashboard summary"""
        return {
            "timestamp": datetime.now().isoformat(),
            "plans": self.get_plan_metrics(),
            "steps": self.get_step_metrics(),
            "tools": {
                "top_failing": self.get_top_failing_tools(),
                "total_tools": len(self.tool_executions)
            },
            "autonomy": self.get_autonomy_metrics(),
            "latency": self.get_latency_metrics(),
            "health": self._get_health_status()
        }
    
    def _get_health_status(self) -> Dict[str, str]:
        """Determine overall system health"""
        health = {}
        
        # Plan success health
        if self.plans_created > 0:
            success_rate = self.plans_completed / self.plans_created
            if success_rate >= 0.9:
                health["plan_success"] = "🟢 Excellent"
            elif success_rate >= 0.75:
                health["plan_success"] = "🟡 Good"
            else:
                health["plan_success"] = "🔴 Poor"
        
        # Step success health
        if self.steps_executed > 0:
            step_success = self.steps_succeeded / self.steps_executed
            if step_success >= 0.95:
                health["step_success"] = "🟢 Excellent"
            elif step_success >= 0.85:
                health["step_success"] = "🟡 Good"
            else:
                health["step_success"] = "🔴 Poor"
        
        # Tool reliability
        failing_tools = self.get_top_failing_tools(1)
        if failing_tools:
            top_failure_rate = float(failing_tools[0]["failure_rate"].rstrip('%'))
            if top_failure_rate < 5:
                health["tool_reliability"] = "🟢 Good"
            elif top_failure_rate < 15:
                health["tool_reliability"] = "🟡 Fair"
            else:
                health["tool_reliability"] = "🔴 Issues Detected"
        
        # Autonomy
        autonomy = self.get_autonomy_metrics()
        acceptance_rate = float(autonomy.get("acceptance_rate", "0").rstrip('%'))
        if acceptance_rate > 80:
            health["user_trust"] = "🟢 High"
        elif acceptance_rate > 50:
            health["user_trust"] = "🟡 Moderate"
        else:
            health["user_trust"] = "🔴 Low"
        
        return health
    
    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than retention period"""
        # Only cleanup periodically (not every call)
        if (datetime.now() - self.last_cleanup).days < 1:
            return
        
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        
        self.execution_times = [p for p in self.execution_times if p.timestamp > cutoff]
        self.autonomy_scores = [p for p in self.autonomy_scores if p.timestamp > cutoff]
        self.success_rates = [p for p in self.success_rates if p.timestamp > cutoff]
        
        self.last_cleanup = datetime.now()
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics as a JSON-serializable dictionary"""
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": self.get_dashboard_summary(),
            "plans": self.get_plan_metrics(),
            "steps": self.get_step_metrics(),
            "tools": self.get_tool_metrics(),
            "autonomy": self.get_autonomy_metrics(),
            "latency": self.get_latency_metrics(),
            "retention_days": self.retention_days
        }

from dataclasses import dataclass, field


@dataclass
class AgentStep:
    tool: str
    reason: str
    status: str = "planned"


@dataclass
class AgentTrace:
    steps: list[AgentStep] = field(default_factory=list)

    def add(self, tool: str, reason: str, status: str = "planned") -> None:
        self.steps.append(AgentStep(tool=tool, reason=reason, status=status))

    def as_dict(self) -> list[dict[str, str]]:
        return [
            {"tool": step.tool, "reason": step.reason, "status": step.status}
            for step in self.steps
        ]


class PolicyAgentOrchestrator:
    """Small, explicit orchestration layer for the policy assistant.

    This is intentionally deterministic rather than marketed as an autonomous
    multi-agent system. It demonstrates the agentic pattern Bain asks about:
    choose a tool, execute it, inspect evidence, and route to a safe fallback
    when the evidence is insufficient.
    """

    def start(self, query: str) -> AgentTrace:
        trace = AgentTrace()
        trace.add(
            tool="policy_search",
            reason="Retrieve approved enterprise policy evidence before generation.",
            status="selected",
        )
        return trace

    def record_retrieval(self, trace: AgentTrace, retrieved: int) -> None:
        status = "completed" if retrieved > 0 else "no_grounded_evidence"
        trace.add(
            tool="hybrid_retrieval",
            reason=f"Fused semantic and lexical retrieval returned {retrieved} grounded result(s).",
            status=status,
        )

    def record_generation(self, trace: AgentTrace) -> None:
        trace.add(
            tool="grounded_generation",
            reason="Generate only from retrieved approved policy context with inline citations.",
            status="completed",
        )

    def record_fallback(self, trace: AgentTrace) -> None:
        trace.add(
            tool="human_escalation",
            reason="Approved evidence was insufficient; route the user to the policy owner or HR instead of guessing.",
            status="completed",
        )

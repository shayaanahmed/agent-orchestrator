from core.domain.agent import AgentRole, Capability

ROLE_CAPABILITIES: dict[AgentRole, set[Capability]] = {
    AgentRole.PLANNER: {Capability.RESEARCH, Capability.DOCUMENTATION},
    AgentRole.CODER: {Capability.CODE_GENERATION, Capability.DOCUMENTATION},
    AgentRole.REVIEWER: {
        Capability.CODE_REVIEW,
        Capability.TESTING,
        Capability.SECURITY_ANALYSIS,
    },
    AgentRole.RESEARCHER: {Capability.RESEARCH, Capability.DOCUMENTATION},
    AgentRole.TESTER: {Capability.TESTING, Capability.CODE_REVIEW},
    AgentRole.DEPLOYER: {Capability.DEPLOYMENT, Capability.SECURITY_ANALYSIS},
}

ROLE_TOOLS: dict[AgentRole, set[str]] = {
    AgentRole.PLANNER: {"artifact_read", "artifact_write"},
    AgentRole.CODER: {"artifact_read", "artifact_write", "sandbox_execute"},
    AgentRole.REVIEWER: {"artifact_read", "sandbox_execute"},
    AgentRole.RESEARCHER: {"artifact_read", "artifact_write"},
    AgentRole.TESTER: {"artifact_read", "artifact_write", "sandbox_execute"},
    AgentRole.DEPLOYER: {"artifact_read", "artifact_write", "sandbox_execute"},
}

SENSITIVE_CAPABILITIES = {Capability.DEPLOYMENT}

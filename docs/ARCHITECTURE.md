# OmiMind Architecture

This diagram shows the major runtime components and their responsibilities.

```mermaid
flowchart LR
    Omi["Omi wearable / microphone"] -->|Transcript segments| Edge["FastAPI application\nVercel or local Uvicorn"]
    Browser["Browser dashboard"] -->|HTTPS / JSON / SSE| Edge

    subgraph Processing["Local processing pipeline"]
        Edge --> Orchestrator["OmiMindOrchestrator"]
        Orchestrator --> Memory["QdrantMemoryAgent"]
        Orchestrator --> Actions["ActionExtractor"]
        Orchestrator --> Synthesis["ExecutiveSynthesizer"]
        Orchestrator --> Tasks["TaskDispatcher"]
        Orchestrator --> Calendar["CalendarScheduler"]
    end

    Memory -->|Vectors + metadata| Qdrant[("Qdrant\nvector memory")]
    Qdrant -->|Semantic recall| Orchestrator

    Edge -->|Optional grounded Q&A| Lyzr["Lyzr Studio\noptional integration"]
    Browser -->|User-controlled links| Outputs["Gmail / Google Calendar / .ics"]
    Tasks --> Outputs
    Calendar --> Outputs

    classDef external fill:#172554,stroke:#60a5fa,color:#dbeafe;
    classDef service fill:#064e3b,stroke:#34d399,color:#d1fae5;
    classDef store fill:#3f1d5b,stroke:#c084fc,color:#f3e8ff;
    class Omi,Browser,Qdrant,Lyzr,Outputs external;
    class Edge,Orchestrator,Memory,Actions,Synthesis,Tasks,Calendar service;
```

The preset demo and custom voice pipeline run locally through the five processing stages. Lyzr Studio is used only when configured for the protected `/ask` endpoint.

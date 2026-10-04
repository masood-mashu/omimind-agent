# OmiMind Data Flow

This diagram follows data from capture through storage, processing, retrieval, and user-controlled delivery.

```mermaid
flowchart TD
    Capture["Voice or transcript capture"] --> Normalize["FastAPI validation and normalization"]
    Normalize --> Session["Session ID + speaker + timestamp"]
    Session --> Embed["128-dimensional embedding"]
    Embed --> Store[("Qdrant collection\n`omi_ambient_memory`")]

    Session --> Pipeline["Processing pipeline"]
    Pipeline --> Extract["Action items\nassignees + deadlines + priority"]
    Pipeline --> Brief["Executive summary\ndecisions + risks"]
    Pipeline --> Dispatch["Follow-up email\nJira-style tickets"]
    Pipeline --> Schedule["Calendar events\nGoogle Calendar URL + iCal"]

    Store --> Search["Semantic + lexical recall"]
    Search --> Answer["Grounded answer with\nspeaker and timestamp"]
    Answer --> Dashboard["Dashboard result"]

    Extract --> Dashboard
    Brief --> Dashboard
    Dispatch --> Dashboard
    Schedule --> Dashboard

    Dashboard -->|Explicit user click| External["Gmail / Calendar / download"]

    Delete["Protected forget endpoint"] -.->|Delete by session or point| Store
    Ask["Protected `/ask` endpoint"] --> Search
    Ask -->|When configured| Lyzr["Lyzr Studio"]

    classDef input fill:#172554,stroke:#60a5fa,color:#dbeafe;
    classDef process fill:#064e3b,stroke:#34d399,color:#d1fae5;
    classDef sensitive fill:#7f1d1d,stroke:#f87171,color:#fee2e2;
    classDef output fill:#3f1d5b,stroke:#c084fc,color:#f3e8ff;
    class Capture,External input;
    class Normalize,Session,Embed,Pipeline,Extract,Brief,Dispatch,Schedule,Search,Answer process;
    class Store,Delete,Ask,Lyzr sensitive;
    class Dashboard output;
```

Transcript data is sensitive. Configure `API_SECRET_KEY`, restrict `ALLOWED_ORIGINS`, and provide Lyzr credentials only when external grounded synthesis is intended.

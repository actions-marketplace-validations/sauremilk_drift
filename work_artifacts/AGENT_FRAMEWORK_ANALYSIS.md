# Microsoft Agent Framework — Technische Analyse und Arbeitsgrundlage

> **Quelle:** `agent-framework.pdf` (655 Seiten, Stand Feb–Apr 2026, Public Preview)
> **Analysiert:** 2026-04-05 | **Workspace:** `mick-gsk/drift`
> **Zweck:** Referenzdokument für Ausbau, Verbesserung und effiziente Nutzung des Agent Frameworks im Drift-Kontext

---

## Inhaltsübersicht

1. [Zweck und Scope des Frameworks](#1-zweck-und-scope-des-frameworks)
2. [Kernkonzepte und Begriffe](#2-kernkonzepte-und-begriffe)
3. [Architekturübersicht](#3-architekturübersicht)
4. [Komponenten und Zusammenspiel](#4-komponenten-und-zusammenspiel)
5. [APIs, SDK-Konzepte und Erweiterungspunkte](#5-apis-sdk-konzepte-und-erweiterungspunkte)
6. [Typische Workflows und Agenten-Muster](#6-typische-workflows-und-agenten-muster)
7. [Best Practices aus der Dokumentation](#7-best-practices-aus-der-dokumentation)
8. [Grenzen, Risiken und offene Punkte](#8-grenzen-risiken-und-offene-punkte)
9. [Relevanz für den Drift-Workspace](#9-relevanz-für-den-drift-workspace)
10. [Konkrete Empfehlungen für Ausbau und Verbesserungen](#10-konkrete-empfehlungen-für-ausbau-und-verbesserungen)
11. [Priorisierte Maßnahmenliste (Impact/Aufwand)](#11-priorisierte-maßnahmenliste)

---

## 1. Zweck und Scope des Frameworks

### Dokumentierte Fakten

- **Microsoft Agent Framework** ist der offizielle Nachfolger von **Semantic Kernel** und **AutoGen**, entwickelt von denselben Teams (S. 2).
- Zwei Hauptkategorien: **Agents** (LLM-Wrapper mit Tools, MCP, Streaming) und **Workflows** (graphbasierte Multi-Step-Orchestrierung mit Checkpointing und HITL).
- Unterstützte Modellprovider: Azure OpenAI, OpenAI, Anthropic, Ollama, Microsoft Foundry, GitHub Copilot, Copilot Studio.
- Status: **Public Preview** (Stand Feb 2026).
- Primär **.NET/C#**-orientiert, Python-Support in Entwicklung (Workflow-Deklaration, Observability, Checkpointing).

### Designprinzipien

| Prinzip | Beschreibung |
|---------|-------------|
| Protocol-agnostic | Agent-Implementierung unabhängig vom Hosting-Protokoll (A2A, AG-UI, OpenAI-API) |
| Middleware-Pipeline | Dreischichtiges Pipeline-Modell (Agent → Context → ChatClient) |
| Progressive Disclosure | Skills laden nur Kontext bei Bedarf (Advertise → Load → Read Resources) |
| DI-first | Agents und Workflows registrieren sich in ASP.NET Core Dependency Injection |
| Builder Pattern | Agents und Clients über `.AsBuilder().Use(...).Build()` erweitert |

### Entscheidungsregel: Agent vs. Workflow

| Agent verwenden, wenn… | Workflow verwenden, wenn… |
|------------------------|--------------------------|
| Aufgabe offen/konversational | Definierte Schritte |
| Autonomes Tool-Planning nötig | Explizite Execution-Order |
| Ein LLM-Aufruf (+Tools) genügt | Mehrere Agents/Funktionen koordinieren |

> **Faustregel (S. 2):** „If you can write a function to handle the task, do that instead of using an AI agent."

---

## 2. Kernkonzepte und Begriffe

| Begriff | Definition (aus PDF) |
|---------|---------------------|
| `AIAgent` | Basisklasse aller Agents. LLM-Wrapper mit RunAsync/RunStreamingAsync, Tools, Session |
| `ChatClientAgent` | Standard-Agent, der an ein `IChatClient` delegiert. Unterstützt alle Chat-basierten Provider |
| `AgentSession` | Konversationskontext (Thread). Serialisierbar für Persistence. Enthält `StateBag` für Key-Value-State |
| `AgentResponse` | Ergebnis eines Agent-Runs. `.Text` für aggregierte Textantwort, `.Messages` für alle Nachrichten |
| `AgentResponseUpdate` | Streaming-Chunk. `.Text` für Textfragment, `.Contents` für Details |
| `Executor` | Workflow-Knoten. Erhält Input über `@handler`, sendet Output via `ctx.SendMessageAsync()` oder `ctx.YieldOutputAsync()` |
| `WorkflowContext` | Kontext innerhalb eines Executors: State-Management, Messaging, Checkpointing, Output |
| `AIContextProvider` | Injiziert zusätzlichen Kontext (Memories, RAG, dynamische Instructions) vor jedem LLM-Call |
| `ChatHistoryProvider` | Verwaltet Gesprächshistorie (InMemory, Cosmos DB, Custom) |
| `FileAgentSkillsProvider` | Entdeckt Skills aus Dateisystem-Verzeichnissen, exponiert `load_skill` / `read_skill_resource` Tools |
| `Middleware` | Interceptors auf Agent-Level (`.Use()`) oder ChatClient-Level (IChatClient Pipeline) |
| `ContinuationToken` | Mechanismus für Background-Responses: Poll/Resume bei lang laufenden Operationen |
| `CheckpointManager` | Persistiert Workflow-Zustand für Fault Tolerance und Resume |
| Declarative Workflow | YAML-definierte Workflows mit PowerFx-Expressions, Agent-Invocations, HITL-Actions |

---

## 3. Architekturübersicht

### 3.1 Agent Runtime Execution Model (S. 19–20)

```
User → Agent → LLM → [Tool Call Required?]
                        ├─ JA:  Execute Tool → Return Result → LLM (Loop)
                        └─ NEIN: Final Response → User
```

**Deterministische Schleife:** Agent iteriert bis Task complete. Tools/MCP werden bei Bedarf aufgerufen, Ergebnisse fließen zurück in den LLM-Kontext.

### 3.2 Agent Pipeline Architecture (S. 30)

```
┌─────────────────────────────────────┐
│  User Request                        │
├─────────────────────────────────────┤
│  1. Agent Middleware (.Use())        │  ← Logging, Validation, Guardrails
├─────────────────────────────────────┤
│  2. Context Layer                    │
│     ├─ ChatHistoryProvider (single)  │  ← Conversation History
│     └─ AIContextProviders[] (list)   │  ← Memory, RAG, Dynamic Instructions
├─────────────────────────────────────┤
│  3. IChatClient Pipeline             │
│     ├─ Client Middleware             │  ← Prompt-Transformation, Logging
│     ├─ FunctionInvokingChatClient    │  ← Tool-Calling Handling
│     └─ Inner ChatClient             │  ← Azure OpenAI / OpenAI / Anthropic…
├─────────────────────────────────────┤
│  LLM Service                         │
└─────────────────────────────────────┘
```

**Execution Flow (S. 32):**
1. Agent Middleware → 2. ChatHistoryProvider lädt History → 3. AIContextProviders injizieren Kontext → 4. IChatClient Middleware → 5. LLM Request → 6. Response zurück durch alle Layer → 7. Providers erhalten Notification über neue Messages

### 3.3 Workflow Architecture

```
WorkflowBuilder ──→ Graph (Executors = Knoten, Edges = Kanten)
                    ├─ Sequential: A → B → C
                    ├─ Concurrent: A → [B, C] → D
                    ├─ Conditional: A → if(cond) B else C
                    └─ SubWorkflows: Nested Graphs
```

**Checkpointing:** Bei jedem Superstep-Boundary wird State serialisiert → Resume von beliebigem Punkt möglich (S. 239, 475–479).

---

## 4. Komponenten und Zusammenspiel

### 4.1 Agent-Typen

| Agent-Typ | Basis | Anwendungsfall |
|-----------|-------|---------------|
| `ChatClientAgent` | Jedes `IChatClient` | Standard-Agent für Chat-basierte Services |
| `FoundryAgent` | Azure AI Foundry | Server-managed, versionierte Agent-Definitionen |
| `A2AAgent` | A2A-Protokoll | Proxy zu Remote-Agents |
| `GitHubCopilotAgent` | Copilot SDK | GitHub-Integration |
| `CopilotStudioAgent` | Copilot Studio | M365-Integration |
| Custom `AIAgent` | Subclass | Vollständige Kontrolle über Verhalten |
| Declarative Agent | YAML/JSON | Konfigurationsbasierte Agent-Definition (S. 51) |

### 4.2 Tools — Provider Support Matrix (S. 67–68)

| Tool-Typ | ChatCompletion | Responses | Assistants | Foundry | Anthropic | Ollama |
|----------|:-:|:-:|:-:|:-:|:-:|:-:|
| Function Tools | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tool Approval (HITL) | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Code Interpreter | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ |
| File Search | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Web Search | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Hosted MCP | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ |
| Local MCP | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 4.3 Context Providers (S. 48, 371–374)

| Provider | Zweck |
|----------|-------|
| `TextSearchProvider` | RAG — Suche über externe Wissensdatenbanken |
| `Neo4j GraphRAG` | Knowledge-Graph basierte RAG mit Cypher-Queries |
| `Neo4j Memory Provider` | Persistentes Agent-Gedächtnis über Knowledge Graph (nur Python) |
| `ChatHistoryMemoryProvider` | Conversation-Memory mit gleitendem Kontext |
| `FileAgentSkillsProvider` | Agent Skills aus Dateisystem |
| Custom `AIContextProvider` | Beliebige Kontext-Injektion vor LLM-Calls |

### 4.4 Hosting & Protokoll-Adapter (S. 15–18)

| Option | Beschreibung | Anwendungsfall |
|--------|-------------|---------------|
| A2A | Agent-to-Agent Protokoll | Multi-Agent-Systeme, Interoperabilität |
| OpenAI-Compatible | Chat Completions / Responses API | OpenAI-kompatible Clients |
| Azure Functions (Durable) | Serverless Agent-Hosting | Long-Running Tasks |
| AG-UI | Web-basierte Agent-UIs mit SSE | Frontend-Integration, CopilotKit |

### 4.5 Middleware-Schichten (S. 122–140)

| Schicht | Scope | Zugriff | Anwendungsbeispiel |
|---------|-------|---------|-------------------|
| Agent Middleware | Agent-Level oder Run-Level | Alle `AIAgent`-Typen | Logging, Guardrails, Security |
| Function Calling Middleware | Per Tool-Call | Nur `ChatClientAgent` | Tool-Audit, Parameter-Validation |
| ChatClient Middleware | Per LLM-Request | Nur `IChatClient`-basierte | Prompt-Transformation, Rate-Limiting |

**Execution Order:** Agent-Level Middleware (outer) → Run-Level Middleware (inner) → Agent Execution (S. 129).

---

## 5. APIs, SDK-Konzepte und Erweiterungspunkte

### 5.1 Agent-Erstellung (Kurzform)

```csharp
// Einfachster Agent
AIAgent agent = chatClient.AsAIAgent(instructions: "...", tools: [...]);

// Builder mit Middleware
var agent = baseAgent
    .AsBuilder()
    .Use(runFunc: SecurityMiddleware, runStreamingFunc: null)
    .UseAIContextProviders(new MyContextProvider())
    .Build();

// Deklarativ aus YAML
AIAgent agent = AgentFactory.CreateFromYaml(yamlContent, openAIClient);

// Hosting mit DI
var pirateAgent = builder.AddAIAgent("pirate", instructions: "...");
pirateAgent.WithAITool(new MyTool()).WithInMemorySessionStore();
```

### 5.2 Workflow-Erstellung

```csharp
// Programmatisch (C#)
var workflow = new AgentWorkflowBuilder(startExecutor: step1)
    .AddEdge(step1, step2)
    .AddEdge(step2, step3)
    .Build();
var result = await workflow.RunAsync("input");

// Sequentiell mit AddWorkflow
builder.AddWorkflow("my-workflow", (sp, key) => {
    var a1 = sp.GetRequiredKeyedService<AIAgent>("agent-1");
    var a2 = sp.GetRequiredKeyedService<AIAgent>("agent-2");
    return AgentWorkflowBuilder.BuildSequential(key, [a1, a2]);
});

// Workflow als Agent exponieren
var workflowAgent = builder.AddWorkflow("wf", ...).AddAsAIAgent();
```

```python
# Programmatisch (Python)
workflow = (WorkflowBuilder(start_executor=upper_executor,
                            checkpoint_storage=checkpoint_storage)
           .add_edge(upper_executor, reverse_executor)
           .build())

async for event in workflow.run_stream("input"):
    print(event)
```

### 5.3 Deklarative Workflows (YAML) — S. 231–260

```yaml
kind: Workflow
trigger:
  kind: OnConversationStart
  id: my_workflow
  actions:
    - kind: InvokeAzureAgent
      agent: { name: ResearcherAgent }
      conversationId: =System.ConversationId
    - kind: If
      condition: =Local.needsReview
      then:
        - kind: Question
          question: { text: "Approve?" }
          variable: Local.decision
    - kind: SendActivity
      activity: { text: =Local.result }
```

**Verfügbare Action-Typen (C# / Python):**

| Kategorie | Actions |
|-----------|---------|
| Variables | SetVariable, SetMultipleVariables, ResetVariable, ClearAllVariables (C#), ParseValue (C#), EditTableV2 (C#) |
| Control Flow | If, ConditionGroup, Foreach, BreakLoop, ContinueLoop, GotoAction, RepeatUntil (Python) |
| Output | SendActivity, EmitEvent (Python) |
| Agent | InvokeAzureAgent |
| Tools | InvokeFunctionTool, InvokeMcpTool (C#) |
| HITL | Question, RequestExternalInput, Confirmation (Python), WaitForInput (Python) |
| Workflow | EndWorkflow, EndConversation, CreateConversation |
| Conversation | AddConversationMessage, CopyConversationMessages (C#) |

**Expression Language:** PowerFx — `=Concat(Local.a, " ", Local.b)`, `=If(Local.x > 5, "yes", "no")`

### 5.4 Key Extension Points

| Extension Point | Mechanismus | Registrierung |
|----------------|-------------|---------------|
| Custom Agent | Subclass `AIAgent` | Override `RunAsyncCore` / `RunStreamingAsyncCore` |
| Custom Tool | `AIFunctionFactory.Create(method)` | Via `tools:` Parameter oder `.WithAITool()` |
| Agent als Tool | `agent.AsAIFunction()` | Ein Agent wird zum Function Tool eines anderen |
| Context Provider | Subclass `AIContextProvider` | `AIContextProviders = [...]` in Options |
| Chat History | Subclass `ChatHistoryProvider` | `ChatHistoryProvider = ...` in Options |
| Agent Middleware | Lambda/Func Delegates | `.AsBuilder().Use(runFunc: ...).Build()` |
| Client Middleware | Lambda/Func Delegates | `chatClient.AsBuilder().Use(...).Build()` |
| Skills | `SKILL.md` Dateien im Filesystem | `FileAgentSkillsProvider(skillPath: ...)` |
| Declarative Agent | YAML-Konfiguration | `AgentFactory.CreateFromYaml(...)` |
| Hosting Protocol | NuGet-Pakete (A2A, AG-UI, OpenAI) | `builder.Services.AddA2AServer()` |

### 5.5 Structured Output (S. 37–41)

```csharp
// Typisiert
AgentResponse<PersonInfo> response = await agent.RunAsync<PersonInfo>("...");

// Via ResponseFormat
var options = new AgentRunOptions {
    ResponseFormat = ChatResponseFormat.ForJsonSchema<MyType>()
};

// Via JSON Schema String (für deklarative Agents)
var options = new AgentRunOptions {
    ResponseFormat = ChatResponseFormat.ForJsonSchema(
        JsonElement.Parse(jsonSchema), "TypeName", "Description")
};
```

> **Einschränkung:** Primitives und Arrays nicht über ResponseFormat unterstützt — Wrapper-Typen verwenden (S. 39).

### 5.6 Background Responses (S. 43–47)

```csharp
AgentRunOptions options = new() { AllowBackgroundResponses = true };
AgentResponse response = await agent.RunAsync("Long task", session, options);

while (response.ContinuationToken is not null) {
    await Task.Delay(TimeSpan.FromSeconds(2));
    options.ContinuationToken = response.ContinuationToken;
    response = await agent.RunAsync(session, options);
}
```

> **Einschränkung:** Nur OpenAI Responses API und Azure OpenAI Responses API unterstützen Background Responses.

---

## 6. Typische Workflows und Agenten-Muster

### 6.1 Multi-Agent Patterns

| Pattern | Beschreibung | Framework-Unterstützung |
|---------|-------------|------------------------|
| Sequential Pipeline | Agents in fester Reihenfolge | `BuildSequential()`, Declarative YAML, `add_edge()` |
| Concurrent Fan-Out | Parallele Verarbeitung, dann Merge | `BuildConcurrent()` |
| Router/Classifier | LLM-basierte Agent-Auswahl | Conditional Edges, If/ConditionGroup in YAML |
| Agent-as-Tool | Ein Agent als Function Tool eines anderen | `.AsAIFunction()` |
| Magentic-One | AutoGen-inspirierte Multi-Agent-Orchestrierung | `MagenticBuilder` (S. 472) |
| Swarm | Handoff-basierte Koordination | In Entwicklung (S. 473) |
| Human-in-the-Loop | Pause → Mensch entscheidet → Resume | `RequestExternalInput`, `ApprovalRequiredAIFunction`, `ctx.request_info()` |

### 6.2 Checkpointing & Fault Tolerance (S. 239, 475–479)

```python
# FileCheckpointStorage persistiert bei jedem Superstep
checkpoint_storage = FileCheckpointStorage(storage_path="./checkpoints")

# Resume von beliebigem Checkpoint
async for event in workflow.run_stream(
    checkpoint_id=saved_checkpoint_id,
    checkpoint_storage=checkpoint_storage
):
    handle(event)
```

**Checkpoint-Inhalte:** Executor State, Shared State, Message Queues, Workflow Position, Pending HITL Requests.

### 6.3 Agent Skills Pattern (S. 57–62)

```
skill-directory/
├── SKILL.md         ← YAML-Frontmatter + Instructions
├── scripts/         ← Executable Code
├── references/      ← Referenzdokumente
└── assets/          ← Templates, Static Resources
```

**Progressive Disclosure:**
1. **Advertise** (~100 Tokens/Skill) — Names + Descriptions im System Prompt
2. **Load** (< 5000 Tokens) — `load_skill` Tool lädt SKILL.md Body
3. **Read Resources** — `read_skill_resource` bei Bedarf

### 6.4 RAG Pattern (S. 48)

```csharp
AIAgent agent = chatClient.AsAIAgent(new ChatClientAgentOptions {
    AIContextProviderFactory = (ctx, ct) => new ValueTask<AIContextProvider>(
        new TextSearchProvider(SearchAdapter, ctx.SerializedState,
                               ctx.JsonSerializerOptions, options))
});
```

---

## 7. Best Practices aus der Dokumentation

### 7.1 Security & Safety (S. 63–66)

- [x] **Function Inputs validieren** — LLM-Argumente sind untrusted Input. Allow-Listing statt Block-Listing.
- [x] **Typ- und Range-Constraints** auf allen Tool-Parametern.
- [x] **Parameterized Queries** bei SQL/Shell — niemals String-Concatenation.
- [x] **System-Messages nur developer-controlled** — kein User-Input in system-role.
- [x] **Tool Approval** für side-effect-Operationen (Daten ändern, E-Mail senden, Löschen).
- [x] **LLM Output as untrusted** — immer validieren/sanitizen vor Rendering, Execution, DB-Queries.
- [x] **Sensitive Data in Logs** nur in Entwicklung (`EnableSensitiveData = true` → nie in Production).
- [x] **Sessions als sensitive Data** behandeln — verschlüsselt speichern, Zugriff kontrollieren.
- [x] **Rate Limiting + Input Length Limits** — Framework setzt keine Grenzen, App-Verantwortung.
- [x] **Context Providers vetting** — Kompromittierter RAG-Store = Indirect Prompt Injection.

### 7.2 Middleware-Patterns

| Pattern | Beschreibung | Seiten |
|---------|-------------|--------|
| Guardrails | Blocked Words, Content Policy Enforcement | S. 132–133 |
| Exception Handling | Try-Catch mit Graceful Fallback | S. 136–137 |
| Result Overrides | Post-Processing (Disclaimer, Truncation) | S. 134–135 |
| Shared State | Cross-Middleware Kommunikation via Dict | S. 138–139 |
| Agent vs Run Scope | Agent-Level (alle Runs) vs Run-Level (per Request) | S. 129–131 |

### 7.3 Observability (S. 52–56)

- **OpenTelemetry Integration** gemäß GenAI Semantic Conventions
- **Traces:** `UseOpenTelemetry(sourceName: ...)` auf ChatClient und `.WithOpenTelemetry()` auf Agent
- **Metrics:** MeterProvider mit gleicher SourceName
- **Logs:** Standard Microsoft.Extensions.Logging mit OpenTelemetry-Exporter
- **Default SourceName:** `Experimental.Microsoft.Agents.AI` (wenn nicht angegeben)
- **Aspire Dashboard** für lokale Visualisierung empfohlen

> **⚠ Warnung (S. 53):** Gleichzeitiges Enablen auf ChatClient UND Agent erzeugt duplizierte Spans.

### 7.4 Skills Best Practices (S. 61)

- Skills wie **Third-Party-Code** behandeln — Review vor Deployment
- **Source Trust** — nur von vertrauenswürdigen Autoren
- **Sandboxing** für Scripts — Filesystem/Network-Zugriff limitieren
- **Audit-Trail** — welche Skills geladen, welche Ressourcen gelesen, welche Scripts ausgeführt

---

## 8. Grenzen, Risiken und offene Punkte

### 8.1 Dokumentierte Einschränkungen

| Einschränkung | Details | Quelle |
|---------------|---------|--------|
| Public Preview | APIs können sich ändern, Breaking Changes möglich | S. 3 |
| Python-Parity | YAML-Actions nicht alle in Python verfügbar (SetTextVariable, ClearAll, InvokeMcpTool, Conversation-Actions fehlen) | S. 257–258 |
| Background Responses | Nur OpenAI/Azure OpenAI Responses API | S. 43 |
| Tool Approval | Nur Responses + Foundry Provider unterstützen es | S. 67–68 |
| Code Interpreter / File Search | Provider-abhängig, nicht universal | S. 75, 77 |
| Structured Output | Nicht alle Agent-Typen unterstützen natives Structured Output | S. 37 |
| Foundry Agent Laufzeit-Modifikation | Tools und Instructions eines FoundryAgent nicht zur Laufzeit änderbar | S. 152 |
| Script-Execution in Skills | Noch nicht in C# unterstützt | S. 59 |
| Neo4j Memory Provider | Nur Python, nicht C# | S. 374 |
| Foundry Local | Nur Python | S. 153 |
| Third-Party-Risiko | Datenfluss zu externen Services liegt in App-Verantwortung | S. 3, 20 |

### 8.2 Offene Fragen und Unsicherheiten

| Thema | Offene Frage |
|-------|-------------|
| **Python Workflow SDK** | Wie weit ist die Parity mit C# Declarative Workflows? YAML-Support scheint eingeschränkt. |
| **MCP Server Connection** | `connection.name` für Hosted MCP "not fully supported yet" (S. 251) — wann? |
| **Swarm Pattern** | Als "in development" markiert (S. 473) — kein Zeitrahmen. |
| **Semantic Kernel EOL** | Migration Guide vorhanden, aber keine klare Timeline für SK-Deprecated-Features. |
| **State Serialization** | Wie werden komplexe State-Typen in Checkpoints serialisiert? JSON-only? |
| **Agent Discovery** | A2A Agent Discovery nur per AgentCard — kein Registry-Service dokumentiert. |
| **Scalability** | Keine Aussagen zu Concurrency-Limits bei Workflow-Execution. InProcessExecution nur single-process? |
| **Cost Control** | Model-Token-Budgets nicht im Framework — rein Service-seitig. |
| **Multi-Language Workflows** | Können C#- und Python-Executors in einem Workflow gemischt werden? Nicht dokumentiert. |

### 8.3 Risiken für den Drift-Workspace

| Risiko | Bewertung | Mitigation |
|--------|-----------|-----------|
| Breaking Changes (Public Preview) | **HOCH** — API-Surface kann sich ändern | Abhängigkeiten pinnen, Abstraction Layer für AF-Calls |
| Python/C# Parity Gap | **MITTEL** — Drift nutzt Python, aber viele Features sind C#-first | Funktionalitäts-Mapping pflegen, C#-Features nicht voraussetzen |
| `from __future__ import annotations` Bug | **HOCH** — Executor-Subklassen mit @handler/@response_handler brechen | Memory-Eintrag vorhanden, in allen neuen Orchestratoren beachten |
| `DefaultAzureCredential` in Prod | **NIEDRIG** — Drift ist CLI-Tool, kein Cloud-Service | Aber bei Control-Plane-Hosting relevant |

---

## 9. Relevanz für den Drift-Workspace

### 9.1 Bestandsaufnahme: Workspace-Integration

Der Drift-Workspace enthält unter `examples/agent-framework/` eine ausgereite **4-Level-Architektur**:

```
Level 4: Meta-Orchestrator (drift_control_plane.py)
  └─ Trigger-Klassifikation → 7 Modi (A–G)

Level 3: Domain-Orchestratoren (orchestrators/*.py)
  ├─ push_readiness.py         — 8 Pre-Push-Gates simulieren
  ├─ engineering_remediation.py — Scan → Diff → FixPlan → Verify
  ├─ governance.py             — Policy-Compliance
  ├─ community_adoption.py     — Community-Metriken
  ├─ release_confidence.py     — Mutation + Regression
  └─ doc_consistency.py        — Docs-Validierung

Level 2: Atomic Agents (agents/*.py) — 23 Einzelagenten
  ├─ Drift Core: scan, diff, fix_plan, verification
  ├─ Evidence: audit_draft, feature_evidence, benchmark
  ├─ Gatekeeper: policy_gate, pr_watchdog
  └─ Analysis: market_data, trend_detection

Level 1: External Systems
  ├─ drift.api (scan, diff, fix_plan, validate, explain)
  ├─ Git/gh CLI
  ├─ LLM Clients (GitHub Models, OpenAI, Azure Foundry)
  └─ pytest, ruff, mypy
```

### 9.2 Mapping: Framework-Features ↔ Drift-Usage

| Framework Feature | Drift Status | Details |
|------------------|-------------|---------|
| Executor + @handler | ✅ Genutzt | Orchestrator-Executors in allen Domain-Orchestratoren |
| @response_handler (HITL) | ✅ Genutzt | Approval-Executors für riskante Operationen |
| WorkflowBuilder + Edges | ✅ Genutzt | Multi-Step Pipelines in allen Orchestratoren |
| FileCheckpointStorage | ✅ Genutzt | `checkpoint_storage.py`, resume via `--resume <run_id>` |
| Agent als Function Tool | ⚠️ Partiell | Einzelne Agents sind @tool-Funktionen, nicht via `.AsAIFunction()` |
| Model Tier Routing | ✅ Custom | `_shared.py` mit 3-Tier-Mapping (fast/balanced/strong) |
| Ledger Pattern | ✅ Custom | `ledgers.py` — Task, Evidence, Policy, RunState |
| Observability | ❌ Nicht genutzt | Kein OpenTelemetry-Setup integriert |
| Declarative Workflows (YAML) | ❌ Nicht genutzt | Alle Workflows sind programmatisch |
| Agent Skills | ❌ Nicht genutzt | Drift hat eigene `.github/skills/` — nicht Agent-Framework-kompatibel |
| Context Providers (RAG) | ❌ Nicht genutzt | Kein RAG/Memory-Provider integriert |
| Middleware Pipeline | ❌ Nicht genutzt | Keine Middleware-Layer auf Agents |
| A2A / AG-UI Hosting | ❌ Nicht genutzt | Control Plane ist CLI-only |
| Structured Output | ⚠️ Partiell | JSON-Parsing manuell, nicht via Framework RunAsync<T> |
| Background Responses | ❌ Nicht genutzt | — |
| Tool Approval (HITL) | ✅ Custom | `autonomy.py` mit eigenem Approval-Mechanismus |
| Purview Integration | ❌ Nicht relevant | Drift ist kein Enterprise-Cloud-Service |

### 9.3 Bekannter Bug: `from __future__ import annotations`

> **KRITISCH:** In Executor-Subklassen mit `@handler`/`@response_handler` darf `from __future__ import annotations` **NICHT** verwendet werden. Das Framework inspiziert Annotations zur Klassendefinitionszeit und kann string-ifizierte `WorkflowContext`-Annotations nicht auflösen → `ValueError`. Alle bestehenden Orchestratoren in `examples/agent-framework/orchestrators/` sind korrekt (ohne Future-Import).

### 9.4 Bekannte Lücke: Control Plane Mode B

> Der erzwungene Control-Plane-Modus B verwendet derzeit `build_engineering_remediation_workflow` statt des neuen `build_push_readiness_workflow`. Der Push-Readiness-Orchestrator ist nicht an den Haupt-Einstiegspunkt verdrahtet.

---

## 10. Konkrete Empfehlungen für Ausbau und Verbesserungen

### 10.1 Sofort umsetzbar (Quick Wins)

| # | Empfehlung | Begründung | Aufwand |
|---|-----------|-----------|---------|
| 1 | **Observability einbauen** — OpenTelemetry-Setup in `_shared.py` oder per Agent | Debugging und Performance-Analyse aller LLM-Calls, Tool-Invocations, Workflow-Steps | Klein |
| 2 | **Mode B verdrahten** — `drift_control_plane.py` Modus B auf `build_push_readiness_workflow` umleiten | Bekannte Lücke schließen | Trivial |
| 3 | **Structured Output nutzen** — `agent.RunAsync<T>()` statt manuelles JSON-Parsing | Reduziert Parsing-Fehler, nutzt Framework-native Validation | Klein |
| 4 | **Middleware für Guardrails** — Token-Limit-Check und Input-Validation als Agent-Middleware | Konsistente Absicherung aller Agent-Runs | Klein |

### 10.2 Mittelfristig (strategisch wertvoll)

| # | Empfehlung | Begründung | Aufwand |
|---|-----------|-----------|---------|
| 5 | **Agent Skills-Kompatibilität** — Drift `.github/skills/` auf Agent Framework SKILL.md-Format migrieren | Progressive Disclosure, Standard-konform, Skills portierbarer | Mittel |
| 6 | **Context Provider für Drift-Findings** — RAG über bisherige Scan-Ergebnisse, Benchmarks, Audit-History | Agents können aus vorherigen Drift-Runs lernen | Mittel |
| 7 | **Declarative Workflow für Standard-Pipelines** — Push-Readiness als YAML | Leichter wartbar, konfigurierbar, testbar | Mittel |
| 8 | **A2A-Hosting** — Control Plane als A2A-Server exponieren | Remote-Agents können Drift-Scans triggern, CI-Integration | Mittel |

### 10.3 Langfristig (transformativ)

| # | Empfehlung | Begründung | Aufwand |
|---|-----------|-----------|---------|
| 9 | **AG-UI Frontend** — Web-UI für Control Plane mit CopilotKit | Visuelles Dashboard für Drift-Analysen, HITL-Approvals, Trend-Visualization | Groß |
| 10 | **Magentic-One Pattern** — Multi-Agent-Orchestrierung mit dynamischer Speaker-Selection | Komplexere Analyse-Szenarien, z.B. Signal-Evaluation mit mehreren Perspektiven | Groß |
| 11 | **Neo4j Memory Provider** — Persistent Memory über Agent-Sessions hinweg | Cross-Repository-Learnings, Trend-Korrelation | Groß |

---

## 11. Priorisierte Maßnahmenliste

Sortiert nach **Impact / Aufwand**-Verhältnis, Policy-konform (Glaubwürdigkeit > Signalpräzision > Verständlichkeit):

| Prio | Maßnahme | Impact | Aufwand | Drift-Priorität |
|:----:|----------|:------:|:-------:|:---------------:|
| 1 | Mode B verdrahten (push_readiness → control_plane) | Mittel | Trivial | Glaubwürdigkeit |
| 2 | Observability (OpenTelemetry) einbauen | Hoch | Klein | Glaubwürdigkeit |
| 3 | Structured Output für Agent-Responses | Mittel | Klein | Signalpräzision |
| 4 | Middleware-Guardrails (Token/Input-Limits) | Mittel | Klein | Glaubwürdigkeit |
| 5 | Skills-Format-Migration | Mittel | Mittel | Einführbarkeit |
| 6 | Context Provider für historische Drift-Daten | Hoch | Mittel | Signalpräzision |
| 7 | Declarative Workflow für Push-Readiness | Mittel | Mittel | Verständlichkeit |
| 8 | A2A-Hosting für Control Plane | Hoch | Mittel | Einführbarkeit |
| 9 | AG-UI Web-Frontend | Hoch | Groß | Einführbarkeit |
| 10 | Magentic-One Orchestrierung | Mittel | Groß | Signalpräzision |
| 11 | Neo4j Memory Integration | Mittel | Groß | Trendfähigkeit |

---

## Anhang A: Kapitelstruktur des PDFs (655 Seiten)

| Seitenbereich | Kapitel / Thema |
|:------------:|----------------|
| 1–3 | Overview, Agent vs Workflow, Herkunft (SK + AutoGen) |
| 4–18 | Get Started Tutorial (6 Steps: Agent → Tools → Multi-Turn → Memory → Workflows → Hosting) |
| 19–34 | Agent Types, Runtime Model, Pipeline Architecture |
| 35–47 | Multimodal, Structured Output, Background Responses |
| 48–50 | RAG (TextSearchProvider) |
| 51 | Declarative Agents (YAML/JSON) |
| 52–56 | Observability (OpenTelemetry) |
| 57–62 | Agent Skills (Specification, Progressive Disclosure, Security) |
| 63–66 | Agent Safety & Security Best Practices |
| 67–78 | Tools Overview, Function Tools, Tool Approval, Code Interpreter, File Search, Web Search |
| 79–120 | MCP Tools (Hosted + Local), Middleware Overview, Context Providers |
| 121–140 | Middleware Deep-Dive (Chat-Level, Agent vs Run Scope, Guardrails, Exception Handling, Shared State) |
| 141–153 | Providers (Azure OpenAI, OpenAI, Foundry, Foundry Local, Anthropic, Ollama) |
| 154–230 | Conversations & Memory, Chat History, Persistent Storage, Custom Agents |
| 231–260 | Declarative Workflows (YAML Actions Reference, Advanced Patterns) |
| 261–370 | Hosting (OpenAI-Compatible API, A2A, AG-UI, Azure Functions, Purview, M365) |
| 371–374 | Neo4j GraphRAG + Memory Provider |
| 375–390 | A2A Integration Deep-Dive, AG-UI Getting Started |
| 391–480 | Workflows Deep-Dive, Checkpointing, Human-in-the-Loop, AutoGen Migration |
| 481–496 | Semantic Kernel Migration Guide, API Reference (Namespaces) |
| 497–655 | Python API Reference, Samples Index, Additional Patterns |

## Anhang B: NuGet-Paket-Übersicht

| Paket | Zweck |
|-------|-------|
| `Microsoft.Agents.AI` | Core Agent-Abstractions |
| `Microsoft.Agents.AI.OpenAI` | OpenAI + Azure OpenAI Provider |
| `Microsoft.Agents.AI.Foundry` | Azure AI Foundry Provider |
| `Microsoft.Agents.AI.Hosting` | ASP.NET Core Hosting-Basis |
| `Microsoft.Agents.AI.Hosting.A2A.AspNetCore` | A2A-Protokoll-Adapter |
| `Microsoft.Agents.AI.Hosting.AGUI.AspNetCore` | AG-UI-Protokoll-Adapter |
| `Microsoft.Agents.AI.Workflows` | Workflow-Engine (Executors, Builder, Checkpointing) |
| `Microsoft.Agents.AI.Workflows.Declarative` | Declarative YAML-Workflows |
| `Microsoft.Agents.AI.Purview` | Microsoft Purview DLP-Integration |
| `Microsoft.Agents.AI.AGUI` | AG-UI Client Library |
| `Neo4j.AgentFramework.GraphRAG` | Neo4j GraphRAG Context Provider |

## Anhang C: Python-Paket-Struktur

```
agent_framework
├── a2a          # A2A Protocol
├── ag_ui        # AG-UI Protocol
├── anthropic    # Anthropic Provider
├── azure        # Azure Provider
├── chatkit      # Chat UI Toolkit
├── declarative  # Declarative Workflows
├── devui        # Development UI
├── lab          # Experimental Features
├── mem0         # Memory Integration
├── microsoft    # Microsoft Provider
├── ollama       # Ollama Provider
├── openai       # OpenAI Provider
├── redis        # Redis State Store
├── exceptions
└── observability
```

---

*Letzte Aktualisierung: 2026-04-05 · Quelle: agent-framework.pdf (655 Seiten, Public Preview Feb–Apr 2026)*

# Oracle Database AI Integration

## Connecting LLMs to Enterprise Data

_Presentation Draft for PowerPoint_

---

## Slide 1: Title

# Oracle Database AI Integration

### SQLcl MCP | Autonomous MCP | Select AI

**Empowering Enterprise AI with Secure Database Access**

_Victor Martin Alvarez | [JAn 29th, 2026]_

---

## Slide 2: The AI-Database Challenge

### What Customers Are Asking

> "How can we let AI assistants safely query our Oracle databases?"

> "We want natural language access to our data, but security is non-negotiable."

> "Can developers use Claude or Copilot with our production data?"

### The Reality

- **80% of enterprise data** lives in databases
- AI assistants are transforming how we work
- But connecting AI to databases raises critical questions:
  - Security & Audit
  - Data Privacy
  - Access Control

---

## Slide 3: Oracle's Three-Pronged Solution

```mermaid
flowchart LR
    subgraph Solutions["Oracle AI-Database Solutions"]
        direction TB
        SelectAI["Select AI<br/>NL2SQL from SQL"]
        Agent["Select AI Agent<br/>Autonomous Workflows"]
        MCP["MCP Servers<br/>External Agent Access"]
    end

    SelectAI --> Agent --> MCP

    style SelectAI fill:#e8f5e9
    style Agent fill:#fff3e0
    style MCP fill:#e3f2fd
```

| Solution            | Direction             | Key Use Case              |
| ------------------- | --------------------- | ------------------------- |
| **Select AI**       | Database → LLM        | NL2SQL for business users |
| **Select AI Agent** | Database orchestrates | Autonomous workflows      |
| **MCP Servers**     | LLM → Database        | Developer AI assistants   |

---

## Slide 4: Understanding the Flow

```mermaid
flowchart TB
    subgraph External["External AI World"]
        Claude["Claude"]
        Copilot["GitHub Copilot"]
        Cursor["Cursor IDE"]
    end

    subgraph Oracle["Oracle Database"]
        MCP["MCP Server"]
        SelectAI["Select AI"]
        Agent["Select AI Agent"]
        Data[(Enterprise Data)]
    end

    subgraph Apps["Business Applications"]
        APEX["Oracle APEX"]
        Custom["Custom Apps"]
    end

    External -->|"MCP Protocol"| MCP
    Apps -->|"SELECT AI"| SelectAI

    MCP --> Agent
    Agent --> SelectAI
    SelectAI --> Data
    Agent --> Data

    style External fill:#e3f2fd
    style Oracle fill:#fff3e0
    style Apps fill:#e8f5e9
```

---

# Part 1: Select AI

---

## Slide 5: Select AI - Natural Language to SQL

### What Is It?

**SQL access to generative AI** — execute natural language queries directly from SQL

### The Magic

```sql
SELECT AI 'What are my top 10 customers by revenue?';
```

The database:

1. Augments your prompt with schema metadata
2. Calls your chosen LLM (OpenAI, Cohere, OCI GenAI)
3. Generates and executes optimized SQL
4. Returns results

---

## Slide 6: Select AI Architecture

```mermaid
sequenceDiagram
    participant App as Business App / APEX
    participant DB as Oracle Database
    participant LLM as External LLM<br/>(OpenAI, Cohere, OCI)

    App->>DB: SELECT AI 'top customers by revenue'
    DB->>DB: Augment prompt with schema metadata
    DB->>LLM: Send augmented prompt
    LLM-->>DB: Return generated SQL
    DB->>DB: Execute SQL
    DB-->>App: Return results

    Note over DB,LLM: Database controls the LLM interaction
```

### Key Point

**The database calls OUT to the LLM** — you control which model, which data is exposed

---

## Slide 7: Select AI Capabilities

| Action       | What It Does                 | Example                               |
| ------------ | ---------------------------- | ------------------------------------- |
| `runsql`     | Generate & execute SQL       | `SELECT AI 'customers in California'` |
| `showsql`    | Show generated SQL only      | `SELECT AI showsql 'top orders'`      |
| `narrate`    | Natural language explanation | `SELECT AI narrate 'revenue trends'`  |
| `chat`       | General conversation         | `SELECT AI chat 'what is ATP?'`       |
| `explainsql` | Explain a query              | `SELECT AI explainsql 'SELECT...'`    |

### Availability

- Oracle Autonomous Database (since 2023)
- Works from any SQL client, APEX, OML notebooks

---

# Part 2: Select AI Agent

---

## Slide 8: Select AI Agent - Autonomous Workflows

### What Is It?

**Build autonomous AI agents inside the database** using the ReAct pattern (Reasoning and Acting)

### Beyond Single Queries

- Multi-turn conversations with memory
- Custom tools (PL/SQL functions, REST APIs)
- Human-in-the-loop approval
- Agent teams for complex tasks

### Availability

- Oracle AI Database 26ai (October 2025)

---

## Slide 9: Select AI Agent Architecture

```mermaid
flowchart TB
    subgraph Agent["Select AI Agent"]
        Reason["Reason"]
        Act["Act"]
        Observe["Observe"]
        Reflect["Reflect"]
    end

    subgraph Tools["Available Tools"]
        SQL["SQL Queries"]
        RAG["RAG / Vector Search"]
        Custom["Custom PL/SQL"]
        REST["REST APIs"]
    end

    subgraph Memory["Memory"]
        Short["Short-term<br/>(Conversation)"]
        Long["Long-term<br/>(Preferences)"]
    end

    Reason --> Act
    Act --> Observe
    Observe --> Reflect
    Reflect --> Reason

    Act --> Tools
    Reflect --> Memory

    style Agent fill:#fff3e0
    style Tools fill:#e8f5e9
    style Memory fill:#e3f2fd
```

---

## Slide 10: Select AI Agent Example

```sql
-- Create a sales advisor agent
BEGIN
  DBMS_CLOUD_AI_AGENT.CREATE_AGENT(
    agent_name  => 'SALES_ADVISOR',
    attributes  => '{"profile_name": "OCI_GENAI",
                     "role": "Sales analyst expert"}',
    description => 'Analyzes sales and provides recommendations'
  );
END;
/

-- Run the agent
SELECT DBMS_CLOUD_AI_AGENT.RUN_AGENT(
  agent_name => 'SALES_ADVISOR',
  prompt     => 'What are the sales trends in EMEA?'
) FROM DUAL;
```

### The Agent Will:

1. Reason about the question
2. Query relevant tables
3. Analyze patterns
4. Provide recommendations

---

# Part 3: SQLcl MCP Server

---

## Slide 11: SQLcl MCP Server - Developer AI Assistants

### What Is It?

**Let Claude, Copilot, and Cursor query your Oracle databases**

### The Model Context Protocol (MCP)

- Open standard by Anthropic (November 2024)
- JSON-RPC 2.0 over stdio
- Oracle was an early adopter

### Availability

- SQLcl 25.2+ (GA July 2025)
- Works with ANY Oracle Database (19c, 21c, 23ai, 26ai)

---

## Slide 12: SQLcl MCP Architecture

```mermaid
flowchart LR
    subgraph Dev["Developer Workstation"]
        Claude["Claude Code<br/>or Copilot/Cursor"]
        SQLcl["SQLcl MCP Server<br/>(sql -mcp)"]
    end

    subgraph DB["Oracle Database"]
        OnPrem[(On-Premises)]
        Cloud[(Cloud)]
        Local[(Local Container)]
    end

    Claude <-->|"stdio<br/>JSON-RPC"| SQLcl
    SQLcl <-->|"SQL*Net"| OnPrem
    SQLcl <-->|"SQL*Net"| Cloud
    SQLcl <-->|"SQL*Net"| Local

    style Claude fill:#e3f2fd
    style SQLcl fill:#fff3e0
```

### Key Point

**Runs locally** — credentials stay on developer's machine

---

## Slide 13: SQLcl MCP Tools

| Tool               | Purpose                                   |
| ------------------ | ----------------------------------------- |
| `list-connections` | Discover saved database connections       |
| `connect`          | Establish session using saved credentials |
| `disconnect`       | End the database session                  |
| `run-sql`          | Execute SQL and PL/SQL                    |
| `run-sqlcl`        | Run SQLcl commands (Data Pump, AWR, etc.) |

### Example Interaction

```
Developer: "Connect to sales_db and show me the top 5 customers"

Claude: [calls list-connections]
        [calls connect("sales_db")]
        [generates SQL]
        [calls run-sql]
        "Here are your top 5 customers..."
```

---

## Slide 14: SQLcl MCP Security

```mermaid
flowchart LR
    subgraph MCP["MCP Interaction"]
        Query["LLM Query<br/>/* Claude Sonnet 4 */"]
    end

    subgraph Audit["Automatic Tracking"]
        VS["V$SESSION<br/>MODULE: Claude"]
        Log["DBTOOLS$MCP_LOG<br/>Full audit trail"]
        Tag["Query Comments<br/>LLM identification"]
    end

    subgraph Integration["Enterprise Integration"]
        AWR["AWR Reports"]
        SIEM["SIEM Tools"]
    end

    Query --> VS
    Query --> Log
    Query --> Tag

    VS --> AWR
    Log --> SIEM

    style MCP fill:#e3f2fd
    style Audit fill:#fff3e0
    style Integration fill:#e8f5e9
```

### Enterprise-Grade Audit

- Every query tagged with LLM model name
- Full session tracking in V$SESSION
- Dedicated audit table for compliance

---

# Part 4: Autonomous MCP Server

---

## Slide 15: Autonomous MCP Server - Enterprise Scale

### What Is It?

**Fully managed MCP server built into Autonomous Database**

### Key Differences from SQLcl MCP

| SQLcl MCP        | Autonomous MCP |
| ---------------- | -------------- |
| Local (stdio)    | Remote (HTTP)  |
| Fixed 5 tools    | Custom tools   |
| User-managed     | Fully managed  |
| Single developer | Multi-user     |

### Availability

- Oracle Autonomous AI Database (GA December 2025)

---

## Slide 16: Autonomous MCP Architecture

```mermaid
flowchart LR
    subgraph Clients["Any Location"]
        Claude["Claude Desktop"]
        Cursor["Cursor IDE"]
        OCI["OCI AI Agents"]
    end

    subgraph ADB["Autonomous AI Database"]
        MCP["MCP Server<br/>(HTTPS endpoint)"]
        Agent["Select AI Agent<br/>Framework"]
        Tools["Custom Tools"]
        Data[(Database)]
    end

    Clients -->|"HTTPS<br/>OAuth"| MCP
    MCP --> Agent
    Agent --> Tools
    Tools --> Data

    style Clients fill:#e3f2fd
    style ADB fill:#fff3e0
```

### Key Point

**MCP exposes Select AI Agent tools** — create once, use from any AI assistant

---

## Slide 17: Autonomous MCP Security Layers

```mermaid
flowchart TB
    subgraph L1["Layer 1: Network Security"]
        ACL["Network ACLs"]
        PE["Private Endpoints"]
        OAuth["OAuth Authentication"]
    end

    subgraph L2["Layer 2: Database Security"]
        VPD["Virtual Private Database"]
        Redaction["Data Redaction"]
        Firewall["SQL Firewall"]
        Vault["Database Vault"]
    end

    subgraph L3["Layer 3: Audit & Compliance"]
        Unified["Unified Audit"]
        Rate["Rate Limiting"]
        Session["Session Controls"]
    end

    L1 --> L2 --> L3

    style L1 fill:#ffebee
    style L2 fill:#fff3e0
    style L3 fill:#e8f5e9
```

### Enterprise Security Stack

All existing Oracle security features work seamlessly with MCP

---

# Part 5: Comparison & Decision Guide

---

## Slide 18: When to Use What?

```mermaid
flowchart TD
    Start([AI + Oracle Database?]) --> Q1{Where does<br/>the LLM run?}

    Q1 -->|"Inside your app"| Q2{Single query or<br/>workflow?}
    Q1 -->|"External AI<br/>(Claude, Copilot)"| MCP["MCP Servers"]

    Q2 -->|"Single NL query"| SelectAI["Select AI"]
    Q2 -->|"Multi-step workflow"| Agent["Select AI Agent"]

    MCP --> Q3{Using ADB?}
    Q3 -->|Yes| ADBMCP["Autonomous MCP"]
    Q3 -->|No| SQLclMCP["SQLcl MCP"]

    style SelectAI fill:#e8f5e9
    style Agent fill:#fff3e0
    style ADBMCP fill:#e3f2fd
    style SQLclMCP fill:#e3f2fd
```

---

## Slide 19: Feature Comparison

| Capability       | Select AI     | Select AI Agent | SQLcl MCP     | Autonomous MCP |
| ---------------- | ------------- | --------------- | ------------- | -------------- |
| **Interface**    | SQL           | PL/SQL          | JSON-RPC      | JSON-RPC       |
| **LLM Choice**   | You configure | You configure   | Agent's LLM   | Agent's LLM    |
| **Custom Tools** | No            | Yes             | No            | Yes            |
| **Memory**       | Conversation  | Short + Long    | Agent manages | Agent manages  |
| **Transport**    | N/A           | N/A             | Local (stdio) | Remote (HTTP)  |
| **Multi-user**   | Yes           | Yes             | No            | Yes            |
| **OAuth**        | N/A           | N/A             | No            | Yes            |
| **Availability** | ADB 2023+     | ADB 26ai        | SQLcl 25.2+   | ADB Dec 2025   |

---

## Slide 20: Layered Architecture

```mermaid
flowchart TB
    subgraph Layer3["External Access Layer"]
        MCP["MCP Servers<br/>(SQLcl + Autonomous)"]
    end

    subgraph Layer2["Orchestration Layer"]
        Agent["Select AI Agent<br/>(Multi-step workflows)"]
    end

    subgraph Layer1["Foundation Layer"]
        SelectAI["Select AI<br/>(NL2SQL)"]
    end

    subgraph Data["Enterprise Data"]
        DB[(Oracle Database)]
    end

    MCP --> Agent
    Agent --> SelectAI
    SelectAI --> DB

    style Layer3 fill:#e3f2fd
    style Layer2 fill:#fff3e0
    style Layer1 fill:#e8f5e9
```

### They're Complementary

An enterprise might use ALL THREE:

- **Select AI** in APEX dashboards
- **Select AI Agent** for automated workflows
- **MCP Servers** for developer AI assistants

---

# Part 6: Industry Use Cases

---

## Slide 21: Financial Services

```mermaid
flowchart LR
    subgraph Use["Use Cases"]
        Fraud["Fraud Pattern Analysis"]
        Risk["Risk Assessment"]
        Comply["Compliance Reporting"]
    end

    subgraph Tech["Technology"]
        MCP["MCP for Analysts"]
        Agent["Agents for Automation"]
        SelectAI["Select AI in Apps"]
    end

    Fraud --> MCP
    Risk --> Agent
    Comply --> SelectAI
```

| Use Case                     | Solution        | Example                                           |
| ---------------------------- | --------------- | ------------------------------------------------- |
| **Ad-hoc fraud analysis**    | SQLcl MCP       | "Show unusual transactions in the last 24 hours"  |
| **Automated risk workflows** | Select AI Agent | Daily risk score calculations with human approval |
| **Compliance dashboards**    | Select AI       | Natural language queries in APEX                  |

---

## Slide 22: Healthcare & Life Sciences

```mermaid
flowchart LR
    subgraph Use["Use Cases"]
        Patient["Patient Data Queries"]
        Clinical["Clinical Trial Analysis"]
        Audit["HIPAA Audit Trails"]
    end

    subgraph Security["Security Requirements"]
        VPD["Row-Level Security"]
        Redact["PII Masking"]
        Audit2["Complete Audit"]
    end

    Use --> Security
```

| Use Case              | Solution         | Security Feature                         |
| --------------------- | ---------------- | ---------------------------------------- |
| **Patient queries**   | Select AI        | VPD policies limit to authorized records |
| **Clinical analysis** | MCP + Autonomous | Data redaction masks sensitive fields    |
| **Audit compliance**  | All solutions    | Unified audit + DBTOOLS$MCP_LOG          |

---

## Slide 23: Retail & E-Commerce

| Use Case                 | Solution        | Business Value                           |
| ------------------------ | --------------- | ---------------------------------------- |
| **Inventory queries**    | Select AI       | Store managers ask "What's running low?" |
| **Sales trend analysis** | SQLcl MCP       | Analysts use Claude to explore data      |
| **Automated reordering** | Select AI Agent | Agent monitors stock, triggers orders    |
| **Customer 360**         | Autonomous MCP  | Support uses AI with secure data access  |

### Example Flow

```
Support Agent: "Show me customer John Smith's order history"
Claude + MCP: [Connects securely, queries with VPD, redacts PII]
              "Here are John's 15 orders this year..."
```

---

## Slide 24: Manufacturing & Supply Chain

```mermaid
flowchart TB
    subgraph Sensors["IoT Data"]
        S1["Production Lines"]
        S2["Quality Sensors"]
        S3["Logistics"]
    end

    subgraph Oracle["Oracle Database"]
        Stream["Streaming Data"]
        History["Historical Data"]
        AI["AI Integration"]
    end

    subgraph Output["AI-Powered Insights"]
        Predict["Predictive Maintenance"]
        Quality["Quality Analysis"]
        Optimize["Supply Optimization"]
    end

    Sensors --> Oracle
    Oracle --> Output
```

| Use Case                   | Solution        | Example                                        |
| -------------------------- | --------------- | ---------------------------------------------- |
| **Maintenance prediction** | Select AI Agent | "Analyze machine X patterns, predict failures" |
| **Quality investigation**  | SQLcl MCP       | Engineers query defect data with Claude        |
| **Supply optimization**    | Select AI       | Dashboard queries in natural language          |

---

## Slide 25: Public Sector

| Use Case              | Solution        | Compliance                           |
| --------------------- | --------------- | ------------------------------------ |
| **Citizen queries**   | Select AI       | FOIA-compliant with redaction        |
| **Budget analysis**   | SQLcl MCP       | Analysts explore spending patterns   |
| **Case management**   | Select AI Agent | Automated case routing with approval |
| **Cross-agency data** | Autonomous MCP  | Secure multi-tenant access           |

### Security Highlight

Oracle's MCP solutions are the ONLY ones with:

- FedRAMP-ready infrastructure (ADB)
- Complete audit trails for compliance
- Fine-grained access control (VPD, Database Vault)

---

# Part 7: Live Demo

---

## Slide 26: Demo Architecture

```mermaid
flowchart TB
    subgraph Dev["Developer Machine"]
        CC["Claude Code<br/>(AI Assistant)"]
        MCP["SQLcl MCP Server"]
    end

    subgraph Local["Local Environment"]
        Podman["Podman Container"]
        ODB["Oracle Database FREE"]
    end

    subgraph Cloud["Oracle Cloud"]
        ADB["Autonomous Database 26ai"]
        Wallet["mTLS Wallet"]
    end

    CC <-->|"MCP Protocol"| MCP
    MCP -->|"hr_local"| ODB
    MCP -->|"hr_cloud"| ADB

    Podman --> ODB
    Wallet --> ADB

    subgraph Schema["HR Schema (identical)"]
        Jobs["jobs"]
        Depts["departments"]
        Emps["employees"]
    end

    ODB -.-> Schema
    ADB -.-> Schema

    style CC fill:#e3f2fd
    style MCP fill:#fff3e0
```

---

## Slide 27: Demo - What We'll Show

### Data Queries

```
"Connect to hr_local and list all employees"
"Show employees by department with their managers"
"What's the salary distribution across departments?"
```

### Database Administration

```
"What is the character-set of the hr_local database?"
"Explain the execution plan for: SELECT * FROM employees"
"What indexes exist on the employees table?"
```

### Cross-Database

```
"Compare employee counts between hr_local and hr_cloud"
```

---

## Slide 28: Demo - Behind the Scenes

```mermaid
sequenceDiagram
    participant User
    participant Claude as Claude Code
    participant MCP as SQLcl MCP
    participant DB as Oracle Database

    User->>Claude: "List all employees"
    Claude->>MCP: list-connections
    MCP-->>Claude: [hr_local, hr_cloud]
    Claude->>MCP: connect("hr_local")
    MCP->>DB: Establish session
    DB-->>MCP: Connected
    Claude->>Claude: Generate SQL
    Claude->>MCP: run-sql("SELECT * FROM employees")
    MCP->>DB: Execute
    DB-->>MCP: Results (CSV)
    MCP-->>Claude: Employee data
    Claude->>User: "Here are the 5 employees..."

    Note over MCP,DB: Every step is auditable
```

---

# Part 8: Roadmap

---

## Slide 29: Oracle Database MCP Evolution

```mermaid
timeline
    title Oracle Database AI Integration Roadmap

    section 2023
        Select AI : NL2SQL in Autonomous Database
                  : Foundation for AI integration

    section 2024
        Nov 2024 : Anthropic releases MCP spec
                 : Oracle evaluates for enterprise

    section 2025
        Jul 2025 : SQLcl MCP Server GA (25.2)
                 : 5 built-in tools
        Oct 2025 : Select AI Agent (26ai)
                 : ReAct pattern, custom tools
        Dec 2025 : Autonomous MCP Server GA
                 : HTTP transport, OAuth, multi-user

    section 2026+
        Coming : SQLcl HTTP transport
              : Centralized enterprise deployment
              : Monthly tool additions
```

---

## Slide 30: What's Coming

| Feature                          | Status         | Impact                             |
| -------------------------------- | -------------- | ---------------------------------- |
| **SQLcl HTTP transport**         | In development | Centralized deployment without ADB |
| **Monthly tool additions**       | Ongoing        | Expanding SQLcl capabilities       |
| **Select AI Agent enhancements** | Continuous     | More built-in tools, better memory |
| **MCP specification updates**    | Tracking       | Oracle follows Anthropic standard  |

### Current Workaround for Centralized SQLcl

Red Hat OpenShift container: `quay.io/rh-ai-quickstart/oracle-sqlcl:0.5.11`

---

# Part 9: Competitive Position

---

## Slide 31: Market Comparison

```mermaid
quadrantChart
    title Database MCP Servers: Enterprise vs. Setup
    x-axis Easy Setup --> Complex Setup
    y-axis Basic Security --> Enterprise Security

    quadrant-1 Enterprise Ready
    quadrant-2 Quick Start
    quadrant-3 Limited Use
    quadrant-4 Power User

    PostgreSQL: [0.15, 0.20]
    MongoDB: [0.25, 0.40]
    Snowflake: [0.30, 0.60]
    Oracle SQLcl: [0.55, 0.85]
    Oracle Autonomous: [0.35, 0.95]
```

---

## Slide 32: Oracle's Competitive Advantages

| Advantage                     | What It Means                                   |
| ----------------------------- | ----------------------------------------------- |
| **Security instrumentation**  | Most comprehensive audit in the market          |
| **Query tagging**             | Every AI query identifiable in AWR/SIEM         |
| **Enterprise security stack** | VPD, Redaction, SQL Firewall, Database Vault    |
| **DBA capabilities**          | Data Pump, AWR, Data Guard via MCP              |
| **Converged database**        | One connection: relational, JSON, graph, vector |
| **Two deployment options**    | Local (SQLcl) or managed (Autonomous)           |

### The Bottom Line

**Oracle is the only database vendor with enterprise-grade AI integration**

---

# Part 10: Call to Action

---

## Slide 33: This Demo Was Built in 3 Days

```mermaid
flowchart LR
    subgraph Day1["Day 1"]
        Infra["Infrastructure<br/>Terraform + Podman"]
    end

    subgraph Day2["Day 2"]
        Schema["HR Schema<br/>Liquibase + Data"]
    end

    subgraph Day3["Day 3"]
        MCP["MCP Integration<br/>+ Documentation"]
    end

    Day1 --> Day2 --> Day3

    subgraph Result["Result"]
        Demo["Complete<br/>End-to-End Demo"]
    end

    Day3 --> Result

    style Result fill:#e8f5e9
```

### AI-Assisted Rapid Development

- Infrastructure as Code (Terraform)
- Schema automation (Liquibase)
- AI-assisted coding (Claude Code)
- Comprehensive documentation

---

## Slide 34: Our Offer to You

### Don't Go to Your Customer with Just a PowerPoint

| Traditional Approach | Our Approach             |
| -------------------- | ------------------------ |
| Slides with promises | Live working demo        |
| "Trust us"           | "Let us show you"        |
| Weeks of preparation | Days with AI assistance  |
| Generic examples     | Your customer's use case |

### We Can Build Your Demo

- Tell us your customer's industry
- Tell us their use case
- We'll build a working POC in days
- You present with confidence

---

## Slide 35: Next Steps

### For Technical Teams

1. Download SQLcl 25.2+
2. Try with Oracle Database FREE (container)
3. Experience the MCP integration firsthand

### For Sales Teams

1. Identify customer AI initiatives
2. Map to Select AI / MCP use cases
3. Request a custom demo build

### Resources

- [SQLcl MCP Documentation](https://docs.oracle.com/en/database/oracle/sql-developer-command-line/)
- [Autonomous MCP Documentation](https://docs.oracle.com/en/cloud/paas/autonomous-database/)
- This demo repository: `github.com/[your-repo]`

---

## Slide 36: Summary

```mermaid
flowchart TB
    subgraph Solutions["Three Complementary Solutions"]
        SelectAI["Select AI<br/>NL2SQL for Apps"]
        Agent["Select AI Agent<br/>Autonomous Workflows"]
        MCP["MCP Servers<br/>AI Assistant Access"]
    end

    subgraph Value["Business Value"]
        Security["Enterprise Security"]
        Audit["Complete Audit"]
        Flex["Deployment Flexibility"]
    end

    subgraph Action["Call to Action"]
        Demo["Build YOUR Demo<br/>in Days, Not Weeks"]
    end

    Solutions --> Value --> Action

    style Action fill:#e8f5e9
```

### Key Messages

1. **Oracle leads** in enterprise AI-database integration
2. **Security first** — audit, VPD, redaction built-in
3. **Choose your approach** — local or managed, query or workflow
4. **Rapid delivery** — AI-assisted demo development in days

---

## Slide 37: Thank You

# Questions?

**Contact Information**

- Victor Martin Alvarez
- victor.martin.alvarez@oracle.com

**Resources**

- Demo Repository: `https://github.com/vmleon/oracle-database-mcp-intro`
- Oracle AI Documentation: `docs.oracle.com`

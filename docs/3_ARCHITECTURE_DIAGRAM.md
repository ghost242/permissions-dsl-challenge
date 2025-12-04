# Architecture Diagrams

## 1. System Architecture Overview (C4 Container Diagram)

```mermaid
C4Container
    title System Architecture - Permission Control System

    Person(user, "API Client", "External application or user")

    System_Boundary(api, "Permission Control API") {
        Container(api_gateway, "API Gateway", "FastAPI", "REST API endpoints for policy management")
        Container(builder, "Builder Component", "Python", "Constructs policy documents")
        Container(evaluator, "Evaluator Component", "Python", "Evaluates permissions")
        Container(filter_engine, "Filter Engine", "Python", "Evaluates filter expressions")
    }

    ContainerDb(database, "PostgreSQL", "Relational Database", "Stores entities and policies")
    ContainerDb(cache, "Redis", "Cache", "Policy caching (optional)")

    Rel(user, api_gateway, "Makes API calls", "HTTPS/JSON")
    Rel(api_gateway, builder, "Builds policies")
    Rel(api_gateway, evaluator, "Evaluates permissions")
    Rel(evaluator, filter_engine, "Evaluates filters")
    Rel(builder, database, "Stores policies", "SQL")
    Rel(evaluator, database, "Fetches policies/entities", "SQL")
    Rel(evaluator, cache, "Cached policies", "Redis Protocol")

    UpdateRelStyle(user, api_gateway, $offsetY="-40", $offsetX="-50")
    UpdateRelStyle(api_gateway, builder, $offsetY="-30")
    UpdateRelStyle(api_gateway, evaluator, $offsetY="30")
```

## 2. Service Component Diagram

```mermaid
graph TB
    subgraph "HTTP Interface Layer"
        A[FastAPI Application]
        B["/resource/policy GET"]
        C["/resource/policy POST"]
        D["/permission-check GET"]
        E["/health GET"]

        A --> B
        A --> C
        A --> D
        A --> E
    end

    subgraph "Business Logic Layer"
        F[Builder Component]
        G[Evaluator Component]
        H[Filter Engine]

        C --> F
        D --> G
        G --> H
    end

    subgraph "Data Access Layer"
        I[Repository Layer]
        J[Policy Repository]
        K[Entity Repository]

        F --> I
        G --> I
        I --> J
        I --> K
    end

    subgraph "Data Storage Layer"
        L[(PostgreSQL Database)]
        M[(Redis Cache)]

        J --> L
        K --> L
        G --> M
    end

    style A fill:#4A90E2
    style F fill:#7ED321
    style G fill:#7ED321
    style H fill:#7ED321
    style L fill:#F5A623
    style M fill:#F5A623
```

## 3. Database Schema (ER Diagram)

```mermaid
erDiagram
    USERS ||--o{ TEAM_MEMBERSHIPS : "belongs to"
    USERS ||--o{ PROJECT_MEMBERSHIPS : "belongs to"
    USERS ||--o{ DOCUMENTS : "creates"
    USERS ||--o| USER_POLICIES : "has"

    TEAMS ||--o{ TEAM_MEMBERSHIPS : "contains"
    TEAMS ||--o{ PROJECTS : "owns"

    PROJECTS ||--o{ PROJECT_MEMBERSHIPS : "contains"
    PROJECTS ||--o{ DOCUMENTS : "contains"

    DOCUMENTS ||--o| RESOURCE_POLICIES : "has"

    USERS {
        string id PK
        string email UK
        string name
        timestamp created_at
        timestamp updated_at
    }

    TEAMS {
        string id PK
        string name
        string plan
        timestamp created_at
        timestamp updated_at
    }

    PROJECTS {
        string id PK
        string team_id FK
        string name
        string visibility
        timestamp created_at
        timestamp updated_at
    }

    DOCUMENTS {
        string id PK
        string project_id FK
        string title
        string creator_id FK
        timestamp deleted_at
        boolean public_link_enabled
        timestamp created_at
        timestamp updated_at
    }

    TEAM_MEMBERSHIPS {
        int id PK
        string user_id FK
        string team_id FK
        string role
        timestamp created_at
        timestamp updated_at
    }

    PROJECT_MEMBERSHIPS {
        int id PK
        string user_id FK
        string project_id FK
        string role
        timestamp created_at
        timestamp updated_at
    }

    USER_POLICIES {
        int id PK
        string user_id FK
        jsonb policy_document
        int version
        timestamp created_at
        timestamp updated_at
    }

    RESOURCE_POLICIES {
        int id PK
        string resource_id UK
        jsonb policy_document
        int version
        timestamp created_at
        timestamp updated_at
    }
```

## 4. Permission Evaluation Flow

```mermaid
sequenceDiagram
    actor Client
    participant API as API Gateway
    participant Evaluator
    participant FilterEngine as Filter Engine
    participant Cache as Redis Cache
    participant DB as PostgreSQL

    Client->>API: GET /permission-check?resourceId&userId&action
    activate API

    API->>Cache: Get resource_policy
    alt Cache Hit
        Cache-->>API: Return cached policy
    else Cache Miss
        API->>DB: SELECT resource_policy
        DB-->>API: Return policy
        API->>Cache: Store in cache
    end

    API->>DB: SELECT document, user, team, project
    DB-->>API: Return entities

    API->>Evaluator: evaluate(user, document, action, policies)
    activate Evaluator

    Note over Evaluator: Extract URNs (teamId, projectId)

    Evaluator->>Evaluator: Check resource properties<br/>(deletedAt, publicLinkEnabled)

    alt Document is deleted
        Evaluator-->>API: Deny (deletedAt != null)
    else Document is public
        Evaluator-->>API: Allow (publicLinkEnabled && action=view)
    else Evaluate policies
        Evaluator->>FilterEngine: Evaluate DENY policies
        activate FilterEngine

        loop For each DENY policy
            FilterEngine->>FilterEngine: Evaluate filters
            Note over FilterEngine: Check conditions<br/>(==, !=, has, etc.)
        end

        alt Any DENY policy matches
            FilterEngine-->>Evaluator: DENY matched
            Evaluator-->>API: Deny
        else No DENY match
            FilterEngine-->>Evaluator: No DENY
            deactivate FilterEngine

            Evaluator->>FilterEngine: Evaluate ALLOW policies
            activate FilterEngine

            loop For each ALLOW policy
                FilterEngine->>FilterEngine: Evaluate filters
            end

            alt Any ALLOW policy matches
                FilterEngine-->>Evaluator: ALLOW matched
                Evaluator-->>API: Allow
            else No ALLOW match
                FilterEngine-->>Evaluator: No ALLOW
                Evaluator-->>API: Deny (default)
            end
            deactivate FilterEngine
        end
    end

    deactivate Evaluator
    API-->>Client: 200 OK {allowed: true/false}
    deactivate API
```

## 5. Policy Document Creation Flow

```mermaid
sequenceDiagram
    actor Admin
    participant API as API Gateway
    participant Builder
    participant Validator as Policy Validator
    participant DB as PostgreSQL
    participant Cache

    Admin->>API: POST /resource/policy<br/>{resourceId, action, target}
    activate API

    API->>Builder: build_policy(options)
    activate Builder

    Builder->>DB: Fetch resource info
    DB-->>Builder: Return document

    Builder->>Builder: Generate policy structure

    Builder->>Validator: validate_policy(policy_doc)
    activate Validator
    Validator->>Validator: Check JSON schema
    Validator->>Validator: Validate URN format
    Validator->>Validator: Check required fields

    alt Validation fails
        Validator-->>Builder: ValidationError
        Builder-->>API: 400 Bad Request
        API-->>Admin: Error response
    else Validation succeeds
        Validator-->>Builder: Valid
        deactivate Validator

        Builder->>DB: INSERT/UPDATE resource_policy
        DB-->>Builder: Success

        Builder->>Cache: Invalidate cached policy
        Cache-->>Builder: OK

        Builder-->>API: PolicyDocument
        deactivate Builder

        API-->>Admin: 201 Created
    end
    deactivate API
```

## 6. Deployment Architecture (Production)

```mermaid
graph TB
    subgraph "External"
        Internet[Internet Users]
        CDN[CloudFront / CloudFlare CDN]
    end

    subgraph "AWS / GCP / Azure Region 1"
        subgraph "Availability Zone 1"
            ALB1[Application Load Balancer]
            API1[API Instance 1]
            API2[API Instance 2]
        end

        subgraph "Availability Zone 2"
            API3[API Instance 3]
            API4[API Instance 4]
        end

        subgraph "Data Layer (Multi-AZ)"
            PrimaryDB[(PostgreSQL Primary)]
            ReplicaDB[(PostgreSQL Replica)]
            RedisCluster[(Redis Cluster)]
        end

        subgraph "Monitoring"
            Prometheus[Prometheus]
            Grafana[Grafana]
        end
    end

    Internet --> CDN
    CDN --> ALB1
    ALB1 --> API1
    ALB1 --> API2
    ALB1 --> API3
    ALB1 --> API4

    API1 --> PrimaryDB
    API2 --> PrimaryDB
    API3 --> PrimaryDB
    API4 --> PrimaryDB

    API1 --> ReplicaDB
    API2 --> ReplicaDB
    API3 --> ReplicaDB
    API4 --> ReplicaDB

    API1 --> RedisCluster
    API2 --> RedisCluster
    API3 --> RedisCluster
    API4 --> RedisCluster

    PrimaryDB -.Replication.-> ReplicaDB

    API1 -.Metrics.-> Prometheus
    API2 -.Metrics.-> Prometheus
    API3 -.Metrics.-> Prometheus
    API4 -.Metrics.-> Prometheus
    PrimaryDB -.Metrics.-> Prometheus
    ReplicaDB -.Metrics.-> Prometheus
    RedisCluster -.Metrics.-> Prometheus

    Prometheus --> Grafana

    style Internet fill:#E8E8E8
    style CDN fill:#4A90E2
    style ALB1 fill:#7ED321
    style API1 fill:#50E3C2
    style API2 fill:#50E3C2
    style API3 fill:#50E3C2
    style API4 fill:#50E3C2
    style PrimaryDB fill:#F5A623
    style ReplicaDB fill:#F5A623
    style RedisCluster fill:#BD10E0
    style Prometheus fill:#FF6B6B
    style Grafana fill:#FF6B6B
```

## 7. Filter Evaluation Engine Logic

```mermaid
flowchart TD
    Start([Start Filter Evaluation]) --> GetFilter[Get Filter Object<br/>{prop, op, value}]
    GetFilter --> ExtractProp[Extract Property Value<br/>from Context]

    ExtractProp --> PropExists{Property<br/>Exists?}
    PropExists -->|No| ReturnNull[Return null<br/>Insufficient Data]
    PropExists -->|Yes| CheckOp{Check<br/>Operator}

    CheckOp -->|"=="| EQ[Compare Equality]
    CheckOp -->|"!="| NE[Compare Not Equal]
    CheckOp -->|">"| GT[Compare Greater Than]
    CheckOp -->|">="| GTE[Compare Greater or Equal]
    CheckOp -->|"<"| LT[Compare Less Than]
    CheckOp -->|"<="| LTE[Compare Less or Equal]
    CheckOp -->|"<>"| NENull[Check Not Null]
    CheckOp -->|"in"| IN[Check In List]
    CheckOp -->|"not in"| NIN[Check Not In List]
    CheckOp -->|"has"| HAS[Check Contains<br/>URN Substring]
    CheckOp -->|"has not"| HASNOT[Check Not Contains]

    EQ --> ReturnBool[Return Boolean]
    NE --> ReturnBool
    GT --> ReturnBool
    GTE --> ReturnBool
    LT --> ReturnBool
    LTE --> ReturnBool
    NENull --> ReturnBool
    IN --> ReturnBool
    NIN --> ReturnBool
    HAS --> ReturnBool
    HASNOT --> ReturnBool

    ReturnBool --> End([End])
    ReturnNull --> End

    style Start fill:#4A90E2
    style End fill:#4A90E2
    style ReturnBool fill:#7ED321
    style ReturnNull fill:#F5A623
    style CheckOp fill:#BD10E0
```

## 8. Scaling Strategy

```mermaid
graph LR
    subgraph "Traffic Pattern"
        T1[Low Traffic<br/>< 10 req/s]
        T2[Medium Traffic<br/>10-50 req/s]
        T3[High Traffic<br/>50-100 req/s]
        T4[Peak Traffic<br/>> 100 req/s]
    end

    subgraph "Infrastructure Response"
        I1[2 API Instances<br/>No Cache]
        I2[3-4 API Instances<br/>Redis Cache Enabled]
        I3[5-7 API Instances<br/>Read Replica Added]
        I4[8-10 API Instances<br/>Multiple Read Replicas<br/>CDN Caching]
    end

    T1 -.Requires.-> I1
    T2 -.Requires.-> I2
    T3 -.Requires.-> I3
    T4 -.Requires.-> I4

    I1 -->|Scale Up| I2
    I2 -->|Scale Up| I3
    I3 -->|Scale Up| I4
    I4 -->|Scale Down| I3
    I3 -->|Scale Down| I2
    I2 -->|Scale Down| I1

    style T1 fill:#D4EDDA
    style T2 fill:#FFF3CD
    style T3 fill:#F8D7DA
    style T4 fill:#F5C6CB
```

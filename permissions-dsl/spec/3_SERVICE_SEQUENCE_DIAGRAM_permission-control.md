# Service Sequence Diagrams - Permission Control Service

## Overview
This document contains detailed sequence diagrams for all major user scenarios in the Permission Control System, showing the complete interaction flow between components.

---

## Scenario 1: Regular User Views Document

**Use Case**: A project editor wants to view a document they have access to

```mermaid
sequenceDiagram
    actor User as User (Editor)
    participant FE as Frontend
    participant API as API Gateway
    participant Eval as Evaluator
    participant Filter as Filter Engine
    participant DB as Database

    User->>FE: Click "View Document"
    FE->>API: GET /permission-check?<br/>resourceId=urn:resource:t1:p1:d1<br/>&userId=user1<br/>&action=can_view

    activate API
    API->>DB: SELECT document WHERE id='d1'
    DB-->>API: {id: d1, deletedAt: null, publicLinkEnabled: false}

    API->>DB: SELECT user WHERE id='user1'
    DB-->>API: {id: user1, email: "editor@example.com"}

    API->>DB: SELECT project_membership<br/>WHERE userId='user1' AND projectId='p1'
    DB-->>API: {userId: user1, projectId: p1, role: 'editor'}

    API->>DB: SELECT resource_policy WHERE resourceId='d1'
    DB-->>API: {policies: [{effect: allow, permissions: [can_view, can_edit]}]}

    API->>Eval: evaluate_permission(user, document, 'can_view', policies)
    activate Eval

    Eval->>Eval: Extract URNs<br/>teamId: t1, projectId: p1

    Eval->>Eval: Check deletedAt<br/>Result: null ✓

    Eval->>Filter: Evaluate DENY policies
    Filter-->>Eval: No DENY match

    Eval->>Filter: Evaluate ALLOW policies
    activate Filter
    Filter->>Filter: Check filter:<br/>project_membership.role IN [editor, admin]
    Filter-->>Eval: ALLOW match ✓
    deactivate Filter

    Eval-->>API: Result: ALLOW
    deactivate Eval

    API-->>FE: 200 OK<br/>{allowed: true, message: "Allow"}
    deactivate API

    FE->>FE: Render document view
    FE-->>User: Display document content
```

---

## Scenario 2: User Attempts to Edit Deleted Document

**Use Case**: Team admin tries to edit a document that has been soft-deleted

```mermaid
sequenceDiagram
    actor User as User (Admin)
    participant FE as Frontend
    participant API as API Gateway
    participant Eval as Evaluator
    participant DB as Database

    User->>FE: Click "Edit Document"
    FE->>API: GET /permission-check?<br/>resourceId=urn:resource:t1:p1:d1<br/>&userId=admin1<br/>&action=can_edit

    activate API
    API->>DB: SELECT document WHERE id='d1'
    DB-->>API: {id: d1, deletedAt: '2025-12-01T10:00:00Z', ...}

    API->>DB: SELECT team_membership<br/>WHERE userId='admin1' AND teamId='t1'
    DB-->>API: {userId: admin1, teamId: t1, role: 'admin'}

    API->>DB: SELECT resource_policy WHERE resourceId='d1'
    DB-->>API: {policies: [...]}

    API->>Eval: evaluate_permission(user, document, 'can_edit', policies)
    activate Eval

    Eval->>Eval: Check deletedAt<br/>Result: NOT NULL ❌

    Note over Eval: DENY policy activated:<br/>"Deleted documents cannot be edited"

    Eval-->>API: Result: DENY<br/>Reason: "Document is deleted"
    deactivate Eval

    API-->>FE: 403 Forbidden<br/>{allowed: false, message: "Deny", reason: "Document is deleted"}
    deactivate API

    FE->>FE: Show error message
    FE-->>User: "This document has been deleted<br/>and cannot be edited"
```

---

## Scenario 3: Free Plan User Attempts to Change Share Settings

**Use Case**: User on free plan tries to enable public link sharing (blocked by policy)

```mermaid
sequenceDiagram
    actor User as User (Free Plan)
    participant FE as Frontend
    participant API as API Gateway
    participant Eval as Evaluator
    participant Filter as Filter Engine
    participant DB as Database

    User->>FE: Click "Enable Public Link"
    FE->>API: GET /permission-check?<br/>resourceId=urn:resource:t1:p1:d1<br/>&userId=user1<br/>&action=can_share

    activate API
    API->>DB: SELECT document WHERE id='d1'
    DB-->>API: {id: d1, projectId: p1, ...}

    API->>DB: SELECT project WHERE id='p1'
    DB-->>API: {id: p1, teamId: t1}

    API->>DB: SELECT team WHERE id='t1'
    DB-->>API: {id: t1, plan: 'free'}

    API->>DB: SELECT user_policy WHERE userId='user1'
    DB-->>API: {policies: [{effect: deny, permissions: [can_share], filter: {prop: 'team.plan', op: '==', value: 'free'}}]}

    API->>Eval: evaluate_permission(user, document, 'can_share', policies)
    activate Eval

    Eval->>Filter: Evaluate DENY policies
    activate Filter

    Filter->>Filter: Evaluate filter:<br/>team.plan == 'free'
    Filter-->>Eval: DENY match ✓
    deactivate Filter

    Note over Eval: DENY policy matched:<br/>"Free plan cannot share"

    Eval-->>API: Result: DENY<br/>Reason: "Free plan restriction"
    deactivate Eval

    API-->>FE: 403 Forbidden<br/>{allowed: false, message: "Deny", reason: "Free plan restriction"}
    deactivate API

    FE->>FE: Show upgrade prompt
    FE-->>User: "Upgrade to Pro plan to enable sharing"
```

---

## Scenario 4: Team Admin Accesses Private Project Document

**Use Case**: Team admin can access documents in any project within their team

```mermaid
sequenceDiagram
    actor Admin as Team Admin
    participant FE as Frontend
    participant API as API Gateway
    participant Eval as Evaluator
    participant Filter as Filter Engine
    participant DB as Database

    Admin->>FE: View document in private project
    FE->>API: GET /permission-check?<br/>resourceId=urn:resource:t1:p1:d1<br/>&userId=admin1<br/>&action=can_view

    activate API
    API->>DB: SELECT document WHERE id='d1'
    DB-->>API: {id: d1, projectId: p1}

    API->>DB: SELECT project WHERE id='p1'
    DB-->>API: {id: p1, teamId: t1, visibility: 'private'}

    API->>DB: SELECT team_membership<br/>WHERE userId='admin1' AND teamId='t1'
    DB-->>API: {userId: admin1, teamId: t1, role: 'admin'}

    Note over API: No project_membership exists<br/>(admin not explicitly in project)

    API->>DB: SELECT user_policy WHERE userId='admin1'
    DB-->>API: {policies: [{effect: allow, permissions: [can_view, can_edit, can_share], filter: {prop: 'user.teamRole', op: '==', value: 'admin'}}]}

    API->>Eval: evaluate_permission(user, document, 'can_view', policies)
    activate Eval

    Eval->>Eval: Extract URNs<br/>user.teamId: t1<br/>document.teamId: t1<br/>Match: ✓

    Eval->>Filter: Evaluate DENY policies
    Filter-->>Eval: No DENY match

    Eval->>Filter: Evaluate ALLOW policies
    activate Filter
    Filter->>Filter: Check filter:<br/>user.teamRole == 'admin'<br/>AND user.teamId == document.teamId
    Filter-->>Eval: ALLOW match ✓
    deactivate Filter

    Note over Eval: Team admin has access<br/>to all team projects

    Eval-->>API: Result: ALLOW
    deactivate Eval

    API-->>FE: 200 OK<br/>{allowed: true, message: "Allow"}
    deactivate API

    FE-->>Admin: Display document
```

---

## Scenario 5: Guest User Accesses Public Link Document

**Use Case**: Unauthenticated or external user views document with publicLinkEnabled=true

```mermaid
sequenceDiagram
    actor Guest as Guest User
    participant FE as Frontend
    participant API as API Gateway
    participant Eval as Evaluator
    participant DB as Database

    Guest->>FE: Open public link
    FE->>API: GET /permission-check?<br/>resourceId=urn:resource:t1:p1:d1<br/>&userId=guest_anonymous<br/>&action=can_view

    activate API
    API->>DB: SELECT document WHERE id='d1'
    DB-->>API: {id: d1, publicLinkEnabled: true, deletedAt: null}

    API->>DB: SELECT user WHERE id='guest_anonymous'
    DB-->>API: null (no user record)

    API->>DB: SELECT resource_policy WHERE resourceId='d1'
    DB-->>API: {policies: [{effect: allow, permissions: [can_view], filter: {prop: 'document.publicLinkEnabled', op: '==', value: true}}]}

    API->>Eval: evaluate_permission(null, document, 'can_view', policies)
    activate Eval

    Eval->>Eval: Check document.publicLinkEnabled<br/>Result: true ✓

    Note over Eval: Public link policy allows<br/>anonymous viewing

    Eval-->>API: Result: ALLOW
    deactivate Eval

    API-->>FE: 200 OK<br/>{allowed: true, message: "Allow (Public Link)"}
    deactivate API

    FE-->>Guest: Display document (read-only)

    Note over Guest, FE: Edit/Delete/Share buttons hidden
```

---

## Scenario 6: Create New Policy Document

**Use Case**: Admin creates a new resource policy for a document

```mermaid
sequenceDiagram
    actor Admin as Document Creator
    participant FE as Frontend
    participant API as API Gateway
    participant Builder as Builder Component
    participant Validator as Validator
    participant DB as Database
    participant Cache as Redis Cache

    Admin->>FE: Configure permissions UI
    FE->>FE: Build policy form:<br/>- Select users/roles<br/>- Choose permissions<br/>- Set conditions

    FE->>API: POST /resource/policy<br/>{<br/>  resourceId: "urn:resource:t1:p1:d1",<br/>  action: "can_edit",<br/>  target: "editor_role"<br/>}

    activate API
    API->>Builder: build_policy(options)
    activate Builder

    Builder->>DB: SELECT document WHERE id='d1'
    DB-->>Builder: {id: d1, creatorId: admin1, projectId: p1}

    Builder->>DB: SELECT project WHERE id='p1'
    DB-->>Builder: {id: p1, teamId: t1}

    Builder->>Builder: Generate policy structure:<br/>{<br/>  resource: {resourceId, creatorId},<br/>  policies: [<br/>    {effect: allow, permissions: [can_edit],<br/>     filter: {prop: 'user.role', op: '==', value: 'editor'}}<br/>  ]<br/>}

    Builder->>Validator: validate_policy(policy_document)
    activate Validator
    Validator->>Validator: Check JSON schema compliance
    Validator->>Validator: Validate URN format
    Validator->>Validator: Verify required fields
    Validator-->>Builder: Valid ✓
    deactivate Validator

    Builder->>DB: INSERT INTO resource_policies<br/>(resource_id, policy_document, version)<br/>VALUES ('d1', {...}, 1)
    DB-->>Builder: Success

    Builder->>Cache: DEL resource_policy:d1
    Cache-->>Builder: OK

    Builder-->>API: PolicyDocument {policyId: "policy_123"}
    deactivate Builder

    API-->>FE: 201 Created<br/>{message: "Policy created", policyId: "policy_123"}
    deactivate API

    FE-->>Admin: "✓ Policy saved successfully"
```

---

## Scenario 7: Bulk Permission Check (Optimization)

**Use Case**: Frontend checks permissions for multiple documents at once (list view)

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as API Gateway
    participant Cache as Redis Cache
    participant Eval as Evaluator
    participant DB as Database

    User->>FE: View document list
    FE->>FE: Need permissions for 10 documents

    Note over FE: Instead of 10 separate requests,<br/>batch into single call

    FE->>API: POST /permission-check/bulk<br/>{<br/>  userId: "user1",<br/>  checks: [<br/>    {resourceId: "d1", action: "can_edit"},<br/>    {resourceId: "d2", action: "can_edit"},<br/>    ...<br/>  ]<br/>}

    activate API
    loop For each check
        API->>Cache: GET resource_policy:{resourceId}
        alt Cache Hit
            Cache-->>API: Cached policy
        else Cache Miss
            API->>DB: SELECT resource_policy
            DB-->>API: Policy document
            API->>Cache: SET resource_policy:{resourceId}
        end

        API->>Eval: evaluate_permission(user, doc, action, policies)
        Eval-->>API: Result
    end

    API-->>FE: 200 OK<br/>{<br/>  results: [<br/>    {resourceId: "d1", allowed: true},<br/>    {resourceId: "d2", allowed: false},<br/>    ...<br/>  ]<br/>}
    deactivate API

    FE->>FE: Show/hide edit buttons per document
    FE-->>User: Render list with permissions
```

---

## Scenario 8: Error Handling - Missing Resource

**Use Case**: Permission check for non-existent document

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as API Gateway
    participant DB as Database

    User->>FE: Access document
    FE->>API: GET /permission-check?<br/>resourceId=urn:resource:t1:p1:invalid<br/>&userId=user1<br/>&action=can_view

    activate API
    API->>DB: SELECT document WHERE id='invalid'
    DB-->>API: null (not found)

    API-->>FE: 404 Not Found<br/>{<br/>  error: "NOT_FOUND",<br/>  message: "resource record not found",<br/>  resourceId: "invalid"<br/>}
    deactivate API

    FE->>FE: Handle error gracefully
    FE-->>User: "Document not found or has been deleted"
```

---

## Scenario 9: Performance Monitoring

**Use Case**: System tracks and alerts on slow permission evaluations

```mermaid
sequenceDiagram
    participant API as API Gateway
    participant Eval as Evaluator
    participant Metrics as Prometheus
    participant Alert as Alerting System

    loop Every API request
        API->>API: Start timer
        API->>Eval: evaluate_permission(...)
        Eval-->>API: Result
        API->>API: Stop timer<br/>Calculate duration

        API->>Metrics: Record metric:<br/>permission_evaluation_time_ms{value: 45}
        API->>Metrics: Increment counter:<br/>permission_checks_total{action: can_view}
    end

    Note over Metrics: Aggregate metrics over 5 minutes

    alt p95 latency > 100ms
        Metrics->>Alert: Trigger alert:<br/>"Permission evaluation slow"
        Alert->>Alert: Send notification to Slack
    else p95 latency < 100ms
        Note over Metrics: System healthy ✓
    end
```

---

## Summary

These sequence diagrams cover:

1. ✅ **Happy path** - Regular permission checks
2. ✅ **DENY policies** - Deleted documents, free plan restrictions
3. ✅ **ALLOW policies** - Team admin access, public links
4. ✅ **Policy management** - Creating policies
5. ✅ **Performance optimizations** - Caching, bulk checks
6. ✅ **Error handling** - Missing resources
7. ✅ **Observability** - Monitoring and alerting

All scenarios follow the architecture defined in `3_ARCHITECTURE.yaml` with proper separation of concerns and clear component boundaries.

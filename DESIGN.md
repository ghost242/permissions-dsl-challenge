# DESIGN

## Actors

* User
    * member type:
        - team member: Users associated in the team
        - project member: Users participate in the project
    * roles
        - viewer: Users who just allowed read-only document, view information about project, team. Optionally allowed action "share".
        - editor: Users who allowed read, edit, delete, share for document, edit information about project, team, invite external user into project, team.
        - admin: Users who creator for document, project, team. Allowed action of "read/view", "edit", "delete", "share/invite" for target document, project, team.

## Component

### Interface

* HTTP server 

    * GET /resource/policy
    * description: Fetch policy document by resourceId
    * request:
        * querystring: 
        * resourceId: resource id for policy document
    * response
        * code: 200
        * body: JSON document(schema by urn:resource:policy:document)

    * POST /resource/policy
    * description: Apply/Update permission policy for resource
    * request:
        * body: 
            | JSON document(schema by urn:resource:policy:document)
            | JSON object that contains fields of "resourceId or URN", "action", "target"
    * response: 
        * code: 201

    * GET /permission-check
    * description: evaluate access permission for user to resource
        ``` mermaid
        sequenceDiagram
            actor user
            participant server
            participant database@{"type":"database"}

            user ->> server: GET /evaluate?resourceId&userId
            activate server
            server ->>+ database: fetch resource_policy by resourceId
            database ->>- server: return resource_policy document
            server ->>+ database: fetch resource record by resourceId
            database ->>- server: return resource record
            server ->> server: build resource_policy document
            server ->>+ database: fetch user_policy by userId
            database ->>- server: return user_policy document
            note over server: Evaluation permission process(resource_policy, user_policy)
            server ->> user: return "allow|deny"
            deactivate server
        ```
    * request:
        * quersytring: 
        * resourceId: resource id for access target
        * userId: user id who request access to resource by id
    * response:
        * body: 
        ```json
        {
            "message": ""
        }
        ```

        * code: 200
        * message: "Allow"

        * code: 404
        * message: "{resource_policy|resource record|user_policy} not found"

        * code: 401
        * message: "Deny"

### Evaluator

* Note: Evaluation permission process
    1. extract team, project from user urn(urn:{teamId}:{projectId}:{userId} -> user.team, user.project)
    2. check user action(view, edit, delete, share)
    3. check resource property
        * publicEnabled: Allow permission range globally(over the team)
        * deletedAt: Always denied for every actions with any permission range
    4. extract team, project from resource urn in policy objects(urn:{teamId}:{projectId}:{resourceId} -> resource.team, resource.project)
        * denied(exception): user.team != resource.team or user.project != resource.project
        * extract user_policy(ies), resource_policy(ies): 
            - user.team == resource.team or user.project == resource.project
            - resource.project == '*' and user.team == reosurce.team
            - matched user.policies[].resourceId both resource.resourceId

    5. compare allowed actions from user.policies and resource.policies
        * allowed:
            - user.action is element of resource_policies[].actions(from step 4)
        * denied(exception):
            - user.action is not in user_policies[].actions

### Builder

* Build policy document
    1. get user provided options("resourceId or URN", "action", "target")
    2. generate policy document model valid of resource_policy schema

## Flow

``` mermaid
flowchart
    user[User]

    user --send resource policy--> interface
    interface --eval result--> user

    subgraph system
        interface[Interface]
        builder[Builder]
        database([Database])
        evaluator[Evaluator]

        database --resource record, policy--> builder
        builder --resource policy--> evaluator
        builder --resource policy--> database
        
        interface --> builder
        evaluator --> interface
    end
```

## Datamodel

``` python
class ActionPolicy:
    id: str  # user, team, project, document
    policyDoc: dict
```


## Sample

1. 삭제된 문서는 아무도 편집/삭제할 수 없음 (Deny)
    ```json
    {
        "ResourcePolicy": {
            "resource": {
                "resourceId": "document id",
            },
            "policies": {
                "filter": {
                    "prop": "document.deletedAt",
                    "op": "<>",
                    "value": null
                },
                "permissions": [
                    "can_view",
                    "can_edit",
                    "can_delete",
                    "can_share"
                ],
                "effect": "deny"
            }
        }
    }
    ```
2. 문서 생성자는 모든 권한을 가짐 (Allow)
    유저
    ``` json
    {
        "UserPolicy": {
            "policies": [
                {
                    "filter": {
                        "prop": "document.creatorId",
                        "op": "==",
                        "value": "user.id"
                    },
                    "permissions": [
                        "can_view",
                        "can_edit",
                        "can_delete",
                        "can_share"
                    ],
                    "effect": "allow"
                }
            ]
        }
    }
    ```
    
    문서
    ```json
    {
        "ResourcePolicy": {
            "resource": {
                "resourceId": "document id",
                "creatorId": "user id"
            }, 
            "policies": [
                {
                    "permissions": ["can_view", "can_edit", "can_delete", "can_share"],
                    "effect": "allow",
                    "filter": {
                        "prop": "document.creatorId",
                        "op": "==",
                        "value": "user.id"
                    }
                }
            ]
        }
    }
    ```
3. 프로젝트의 editor/admin 역할을 가진 사용자는 편집 가능 (Allow)
    editor 유저
    ``` json
    {
        "UserPolicy": {
            "policies": [
                {
                    "description": "User role of editor",
                    "filter": {
                        "prop": "document.id",
                        "op": "==",
                        "value": "urn:{teamId}:{projectId}:{documentId}"
                    },
                    "permissions": [
                        "can_view",
                        "can_edit",
                    ],
                    "effect": "allow"
                }
            ]
        }
    }
    ``` 
    admin 유저
    ``` json
    {
        "UserPolicy": {
            "policies": [
                {
                    "description": "User role of admin",
                    "filter": {
                        "prop": "document.id",
                        "op": "has",
                        "value": "urn:{teamId}:{projectId}"
                    },
                    "permissions": [
                        "can_view",
                        "can_edit",
                        "can_delete",
                        "can_share"
                    ],
                    "effect": "allow"
                }
            ]
        }
    }
    ```

    문서
    ```json
    {
        "ResourcePolicy": {
            "resource": {
                "resourceId": "document id",
                "creatorId": "creator id"
            }, 
            "policies": [
                {
                    "description": "Admin(project or team) user",
                    "permissions": ["can_view", "can_edit", "can_delete", "can_share"],
                    "effect": "allow",
                    "filter": {
                        "prop": "user.id",
                        "op": "==",
                        "value": "admin user id"
                    }
                },
                {
                    "description": "Editor user",
                    "permissions": ["can_view", "can_edit"],
                    "effect": "allow",
                    "filter": {
                        "prop": "user.id",
                        "op": "==",
                        "value": "editor user id"
                    }
                },
            ]
        }
    }
    ```
4. 팀의 admin 역할을 가진 사용자는 팀 내 모든 프로젝트의 문서에 대해 can_view, can_edit, can_share 권한을 가짐 (Allow)
    admin 유저
    ``` json
    {
        "UserPolicy": {
            "policies": [
                {
                    "filter": {
                        "prop": "user.id",
                        "op": "has",
                        "value": "urn:{teamId}"
                    },
                    "description": "for every project in team",
                    "permissions": [
                        "can_view",
                        "can_edit",
                        "can_delete",
                        "can_share"
                    ],
                    "effect": "allow"
                }
            ]
        }
    }
    ``` 
5. private 프로젝트의 문서는 프로젝트 멤버 또는 팀 admin만 접근 가능 (Deny for others)
    문서
    ```json
    {
        "ResourcePolicy": {
            "resource": {
                "resourceId": "document id",
                "creatorId": "user id"
            }, 
            "policies": [
                {
                    "description": "admin user permission",
                    "permissions": [
                        "can_view",
                        "can_edit",
                        "can_delete",
                        "can_share"
                    ],
                    "effect": "allow",
                    "filter": {
                        "prop": "user.id",
                        "op": "==",
                        "": "urn:{teamId}:{projectId}:{adminId}"
                    }
                },
                {
                    "description": "Default view permission for every project member",
                    "permissions": [
                        "can_view",
                    ],
                    "effect": "allow",
                    "filter": {
                        "prop": "user.id",
                        "op": "has",
                        "value": "urn:{teamId}:{projectId}"
                    }
                }
            ]
        }
    }
    ```
6. free 플랜 팀의 문서는 공유 설정 변경 불가 (Deny)
    free 유저
    ``` json
    {
        "UserPolicy": {
            "policies": [
                {
                    "filter": {
                        "prop": "project.plan",
                        "op": "==",
                        "value": "free"
                    },
                    "description": "free team user does not allow change share option",
                    "permissions": [
                        "can_share"
                    ],
                    "effect": "deny"
                }
            ]
        }

    }
    ```

7. publicLinkEnabled가 true인 문서는 누구나 볼 수 있음 (Allow)
    문서
    ```json
    {
        "ResourcePolicy": {
            "resource": {
                "resourceId": "document id",
                "creatorId": "user id",
                "isPublic": true
            }, 
            "policies": [
                {
                    "permissions": ["can_view"],
                    "effect": "allow",
                    "filter": {
                        "prop": "document.publicLinkEnabled",
                        "op": "==",
                        "value": true
                    }
                }
            ]
        }
    }
    ```

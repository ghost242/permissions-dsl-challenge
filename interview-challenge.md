# 권한 DSL 시스템 설계 및 구현 과제

## 배경

협업 기반의 문서 관리 플랫폼을 운영하고 있습니다. 사용자들은 프로젝트와 팀에 속해 있으며, 문서에 대한 다양한 권한(보기, 편집, 삭제 등)을 가질 수 있습니다. 최근 권한 시스템이 복잡해지면서 다음과 같은 문제들이 발생하고 있습니다:

### 현재 문제점
1. **복잡한 권한 로직**: 권한 확인 코드가 여러 곳에 산재되어 있고, 수정이 어려움
2. **성능 문제**: 권한 확인을 위한 데이터베이스 쿼리가 비효율적
3. **디버깅 어려움**: 특정 사용자가 왜 권한이 있거나 없는지 추적하기 어려움
4. **일관성 부족**: 여러 서비스(API, 실시간 서버 등)에서 권한 로직이 중복되고 불일치

### 요구사항

`references` 디렉토리 아래 다양한 권한 정책 엔진을 참고하여, 다음을 만족하는 권한 시스템을 설계하고 핵심 부분을 구현하세요:

1. **정책 기반 접근**: 권한 규칙을 독립적인 정책(Policy)으로 정의
2. **선언적 DSL**: JSON 등 직렬화 가능한 표현식으로 권한 로직 표현
3. **데이터/로직 분리**: 데이터 로딩과 권한 평가 로직 완전 분리
4. **크로스 플랫폼**: 언어에 독립적으로 동작 가능한 구조

---

## Part 1: 시스템 설계

### 1.1 도메인 모델 정의

다음 엔티티들이 있는 시스템을 가정합니다:

```typescript
// 사용자
interface User {
  id: string;
  email: string;
  name: string;
}

// 팀
interface Team {
  id: string;
  name: string;
  plan: 'free' | 'pro' | 'enterprise';
}

// 프로젝트
interface Project {
  id: string;
  name: string;
  teamId: string;
  visibility: 'private' | 'public';
}

// 문서
interface Document {
  id: string;
  title: string;
  projectId: string;
  creatorId: string;
  deletedAt: Date | null;
  publicLinkEnabled: boolean;
}

// 팀 멤버십
interface TeamMembership {
  userId: string;
  teamId: string;
  role: 'viewer' | 'editor' | 'admin';
}

// 프로젝트 멤버십
interface ProjectMembership {
  userId: string;
  projectId: string;
  role: 'viewer' | 'editor' | 'admin';
}
```

### 1.2 권한 DSL 설계

다음 요구사항을 만족하는 DSL을 설계하세요:

**권한 종류**:
- `can_view`: 문서 보기
- `can_edit`: 문서 편집
- `can_delete`: 문서 삭제
- `can_share`: 문서 공유 설정 변경

**정책 예시**:
1. 삭제된 문서는 아무도 편집/삭제할 수 없음 (Deny)
2. 문서 생성자는 모든 권한을 가짐 (Allow)
3. 프로젝트의 editor/admin 역할을 가진 사용자는 편집 가능 (Allow)
4. 팀의 admin 역할을 가진 사용자는 팀 내 모든 프로젝트의 문서에 대해 can_view, can_edit, can_share 권한을 가짐 (Allow)
5. private 프로젝트의 문서는 프로젝트 멤버 또는 팀 admin만 접근 가능 (Deny for others)
6. free 플랜 팀의 문서는 공유 설정 변경 불가 (Deny)
7. publicLinkEnabled가 true인 문서는 누구나 볼 수 있음 (Allow)

**과제**:

```markdown
1. Expression DSL의 구조를 설계하세요
   - BinaryExpression (예: ["document.deletedAt", "<>", null])
   - 논리 연산자 (and, or, not)
   - 필드 참조 방식

2. Policy 클래스/인터페이스 구조를 설계하세요
   - 필수 속성들 (effect, permissions, applyFilter 등)
   - 위 7개 정책 예시를 실제 DSL로 표현해보세요

3. 시스템 아키텍처를 다이어그램으로 그리세요
   - PolicyEngine, ApplyEvaluator, DataLoader의 역할과 관계
   - 데이터 흐름도

4. 데이터 로딩 전략을 설명하세요
   - 어떤 데이터를 언제 로드할지
   - 지연 로딩(Lazy Loading)을 어떻게 구현할지
```

---

## Part 2: 핵심 컴포넌트 구현

선호하는 언어(TypeScript, Python, Go, Java 등)를 선택하여 다음을 구현하세요.

### 2.1 Expression DSL 및 Evaluator 구현

```typescript
// 예시: TypeScript로 구현할 경우의 타입 정의

type FieldName = string; // "document.deletedAt", "user.id" 등
type Value = string | number | boolean | null;

type BinaryExpression = [
  FieldName,
  '=' | '<>' | '>' | '<' | '>=' | '<=',
  Value | { ref: FieldName }
];

type Expression =
  | BinaryExpression
  | { and: Expression[] }
  | { or: Expression[] }
  | { not: Expression };

// 구현해야 할 함수
function evaluateExpression(
  expr: Expression,
  data: Record<string, Record<string, Value>>
): boolean | null {
  // TODO: 구현
  // - true/false: 확정적으로 평가 가능
  // - null: 데이터 부족으로 평가 불가 (지연 로딩용)
}
```

**구현 요구사항**:
- `and`, `or`, `not` 연산자 처리
- 필드 참조 (`{ ref: "field.name" }`) 처리
- 데이터가 부족한 경우 `null` 반환 (지연 로딩 지원)
- 타입 비교 (문자열, 숫자, boolean, null, Date)

**테스트 케이스 작성**:
```typescript
const testCases = [
  {
    name: "Simple equality",
    expr: ["user.id", "=", "123"],
    data: { user: { id: "123" } },
    expected: true
  },
  {
    name: "AND operation",
    expr: {
      and: [
        ["document.deletedAt", "=", null],
        ["user.role", "=", "admin"]
      ]
    },
    data: {
      document: { deletedAt: null },
      user: { role: "admin" }
    },
    expected: true
  },
  {
    name: "Missing data returns null",
    expr: ["document.title", "=", "Test"],
    data: { user: { id: "123" } }, // document 데이터 없음
    expected: null
  },
  // 추가 테스트 케이스 5개 이상 작성
];
```

### 2.2 Policy 시스템 구현

```typescript
interface Policy {
  name: string;
  description: string;
  effect: 'allow' | 'deny';
  permissions: string[];
  applyFilter: Expression;
  requiredData?: string[]; // 필요한 데이터 테이블 목록
}

class PolicyEngine {
  private policies: Policy[] = [];

  addPolicy(policy: Policy): void {
    // TODO: 구현
  }

  async hasPermission(
    resource: any,
    user: any,
    permission: string
  ): Promise<boolean> {
    // TODO: 구현
    // 1. permission에 해당하는 모든 정책 필터링
    // 2. 필요한 데이터 파악
    // 3. 데이터 로드
    // 4. Deny 정책 평가 (하나라도 true면 거부)
    // 5. Allow 정책 평가 (하나라도 true면 허용)
    // 6. 기본값은 거부
  }
}
```

**구현 요구사항**:
- Part 1.2에서 정의한 7개 정책을 코드로 구현
- DENY 정책이 ALLOW보다 우선순위 높음
- 정책 평가 순서 최적화 (가능한 빨리 결정)

### 2.3 데이터 로더 구현

```typescript
interface DataLoader {
  load(
    resource: any,
    user: any,
    requiredFields: Set<string>
  ): Promise<Record<string, Record<string, Value>>>;
}

class MockDataLoader implements DataLoader {
  async load(
    resource: any,
    user: any,
    requiredFields: Set<string>
  ): Promise<Record<string, Record<string, Value>>> {
    // TODO: 구현
    // - requiredFields를 파싱하여 어떤 테이블의 어떤 필드가 필요한지 파악
    // - 테스트용 mock 데이터 반환
    // - 실제로는 데이터베이스 쿼리를 수행
  }
}
```

---

## Part 3: 최적화 및 확장

### 3.1 성능 최적화

다음 중 하나 이상을 구현하거나 설계하세요:

**옵션 A: 지연 로딩 및 단락 평가**
```typescript
// 데이터를 단계적으로 로드하면서 정책 평가
// 조기 종료 가능한 경우 즉시 반환
```

**옵션 B: 의존성 분석**
```typescript
// Expression에서 필요한 모든 필드를 추출하는 함수
function extractRequiredFields(expr: Expression): Set<string> {
  // TODO: 구현
}
```

**옵션 C: 결과 캐싱**
```typescript
// 동일한 (resource, user, permission) 조합에 대해 캐싱
// TTL 및 무효화 전략 설계
```

### 3.2 디버깅 기능

```typescript
interface EvaluationTrace {
  policyName: string;
  effect: 'allow' | 'deny';
  expression: Expression;
  result: boolean | null;
  evaluatedAt: Date;
  dataUsed: Record<string, any>;
  subTraces?: EvaluationTrace[]; // and/or/not 내부 평가
}

function evaluateWithTrace(
  expr: Expression,
  data: Record<string, Record<string, Value>>
): { result: boolean | null; trace: EvaluationTrace } {
  // TODO: 구현
  // 평가 과정을 상세히 기록하여 디버깅 가능하게 만들기
}
```

### 3.3 정적 분석 (선택)

```typescript
// 잠재적 버그를 찾는 린터 구현
function lintPolicy(policy: Policy): string[] {
  const errors: string[] = [];

  // 체크할 내용:
  // 1. 필드 참조 비교 시 null 체크 누락
  // 2. 항상 true/false인 조건
  // 3. 도달 불가능한 조건
  // 4. 순환 참조

  // TODO: 구현

  return errors;
}
```

---

## Part 4: 종합 시나리오 테스트

다음 시나리오들에 대해 시스템이 올바르게 동작하는지 테스트를 작성하세요:

### 시나리오 1: 일반 프로젝트 멤버
```typescript
const user = { id: "u1", email: "user@example.com" };
const team = { id: "t1", plan: "pro" };
const project = { id: "p1", teamId: "t1", visibility: "private" };
const document = {
  id: "d1",
  projectId: "p1",
  creatorId: "u2",
  deletedAt: null,
  publicLinkEnabled: false
};
const teamMembership = { userId: "u1", teamId: "t1", role: "viewer" };
const projectMembership = { userId: "u1", projectId: "p1", role: "editor" };

// 예상 결과:
// can_view: true (프로젝트 멤버이고 private)
// can_edit: true (editor 역할)
// can_delete: false (생성자가 아님)
// can_share: true (pro 플랜)
```

### 시나리오 2: 삭제된 문서
```typescript
const user = { id: "u1", email: "creator@example.com" };
const team = { id: "t1", plan: "pro" };
const project = { id: "p1", teamId: "t1", visibility: "private" };
const document = {
  id: "d1",
  projectId: "p1",
  creatorId: "u1",
  deletedAt: new Date(),
  publicLinkEnabled: false
};
const teamMembership = { userId: "u1", teamId: "t1", role: "admin" };
const projectMembership = { userId: "u1", projectId: "p1", role: "admin" };

// 예상 결과:
// can_view: true (생성자)
// can_edit: false (삭제됨 - DENY 정책)
// can_delete: false (삭제됨 - DENY 정책)
// can_share: false (삭제됨 - DENY 정책)
```

### 시나리오 3: Free 플랜 제한
```typescript
const user = { id: "u1", email: "user@example.com" };
const team = { id: "t1", plan: "free" };
const project = { id: "p1", teamId: "t1", visibility: "public" };
const document = {
  id: "d1",
  projectId: "p1",
  creatorId: "u2",
  deletedAt: null,
  publicLinkEnabled: false
};
const teamMembership = { userId: "u1", teamId: "t1", role: "viewer" };
const projectMembership = { userId: "u1", projectId: "p1", role: "admin" };

// 예상 결과:
// can_view: true (프로젝트 멤버)
// can_edit: true (프로젝트 admin)
// can_delete: false (생성자가 아님)
// can_share: false (free 플랜 - DENY 정책)
```

### 시나리오 4: 팀 Admin - Private 프로젝트 접근 가능
```typescript
const user = { id: "u1", email: "admin@example.com" };
const team = { id: "t1", plan: "pro" };
const project = { id: "p1", teamId: "t1", visibility: "private" };
const document = {
  id: "d1",
  projectId: "p1",
  creatorId: "u2",
  deletedAt: null,
  publicLinkEnabled: false
};
const teamMembership = { userId: "u1", teamId: "t1", role: "admin" };
// projectMembership 없음 - 프로젝트에 직접 포함되지 않음

// 예상 결과:
// can_view: true (팀 admin은 팀 내 모든 private 프로젝트 접근 가능)
// can_edit: true (팀 admin 권한으로 편집 가능)
// can_delete: false (생성자가 아님)
// can_share: true (pro 플랜 + 팀 admin)
```

### 시나리오 5: 팀 Editor - Private 프로젝트 접근 불가
```typescript
const user = { id: "u1", email: "editor@example.com" };
const team = { id: "t1", plan: "pro" };
const project = { id: "p1", teamId: "t1", visibility: "private" };
const document = {
  id: "d1",
  projectId: "p1",
  creatorId: "u2",
  deletedAt: null,
  publicLinkEnabled: false
};
const teamMembership = { userId: "u1", teamId: "t1", role: "editor" };
// projectMembership 없음 - 프로젝트에 직접 포함되지 않음

// 예상 결과:
// can_view: false (팀 editor는 private 프로젝트에 명시적으로 포함되어야 함)
// can_edit: false (접근 불가)
// can_delete: false (접근 불가)
// can_share: false (접근 불가)
```

### 시나리오 6: Public Link 활성화 - 누구나 볼 수 있음
```typescript
const user = { id: "u1", email: "guest@example.com" };
const team = { id: "t1", plan: "pro" };
const project = { id: "p1", teamId: "t1", visibility: "private" };
const document = {
  id: "d1",
  projectId: "p1",
  creatorId: "u2",
  deletedAt: null,
  publicLinkEnabled: true
};
// teamMembership 없음 - 팀 멤버가 아님
// projectMembership 없음 - 프로젝트 멤버가 아님

// 예상 결과:
// can_view: true (publicLinkEnabled가 true이면 누구나 볼 수 있음)
// can_edit: false (멤버가 아니므로 편집 불가)
// can_delete: false (멤버가 아니므로 삭제 불가)
// can_share: false (멤버가 아니므로 공유 설정 변경 불가)
```

---

## 제출 방법

다음을 포함하여 제출하세요:

1. **설계 문서** (`DESIGN.md`)
   - 시스템 아키텍처 다이어그램
   - DSL 문법 정의
   - 주요 설계 결정 및 트레이드오프

2. **구현 코드**
   - 소스 코드 (적절한 디렉토리 구조)
   - 단위 테스트
   - 통합 테스트 (시나리오 기반)

3. **README.md**
   - 프로젝트 개요
   - 설치 및 실행 방법
   - 예제 사용법
   - 개선 가능한 부분 및 제약사항

4. **성능 분석** (선택)
   - 벤치마크 결과
   - 최적화 전후 비교

---

## 참고 자료

- [Figma 권한 DSL 사례](references/figma-permissions-dsl-ko.md)
- [Open Policy Agent (OPA) - Rego 언어](references/opa-rego-language-ko.md)
- [Zanzibar 인증 시스템](references/zanzibar-authorization-system-ko.md)
- [Oso - Polar 언어](references/oso-polar-language-ko.md)
- 주요 개념:
  - Policy-based Access Control (PBAC)
  - Domain Specific Language (DSL)
  - Expression Evaluation
  - Lazy Loading
  - Static Analysis

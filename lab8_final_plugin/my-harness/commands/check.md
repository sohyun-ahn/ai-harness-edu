---
description: 방금 만든 결과물을 verifier 서브에이전트로 검증한다
argument-hint: [검증할 파일이나 설명]
---

<!-- TODO(실습): 우리 팀 검증 절차로 바꾼다. 플러그인 명령은 /my-harness:check 로 부른다. -->

verifier 서브에이전트에게 다음을 넘겨 검증해라: $ARGUMENTS

인자가 없으면 이 대화에서 마지막으로 만든 결과물을 넘긴다. verdict 가 fail 이면 문제 목록을 그대로 보여 주고 고칠지 묻는다.

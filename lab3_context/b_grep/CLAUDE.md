# 설비 이력 조회 Agent

<!-- TODO(실습): 「필요한 줄만 찾기」 지시. -->

설비 이력은 `data/equipment_log.csv` 에 있다 (열: date,equip_id,type,event,downtime_min,note).
파일 전체를 Read 하지 않는다. Grep 으로 설비 ID 가 들어간 줄만 찾아서 답한다.

# D4 Standard Output Report

## Input files read from `raw/d4/`
- chat_logs_raw.jsonl
- knowledge_raw.txt
- preferences_raw.csv
- tool_result_raw.jsonl
- config_manual.yaml

## Output files written to `standard/`
- chat_logs.json
- tool_results.json
- preferences.json
- knowledge.json
- report.md

## Record counts
- chat_logs: 16
- tool_results: 8
- preferences: 12
- knowledge: 5

## 停顿词统计
- 嗯: 8
- 然后: 6
- 呃: 5
- 那个: 5
- 就是: 4
- 啊: 2

## Sample records containing停顿词
- {"session": "S100", "uid": "u001", "role": "user", "text": "  嗯…那个…帮我把月报导出成PDF，要【简洁版】  ", "ts": "2026-06-04 09:00:00"}
- {"session": "S101", "uid": "U002", "role": "user", "text": "呃…就是…以后回复能不能别用 emoji 啊 🙏😅", "ts": "2026/6/4 10:15"}
- {"session": "S102", "uid": "u003", "role": "user", "text": "然后然后帮我查：奇麟 系统 怎么 更新 驱动？？？", "ts": "2026年6月4日 14:00"}
- {"session": "S100", "uid": "u001", "role": "user", "text": "  嗯…那个…帮我把月报导出成PDF，要【简洁版】  ", "ts": "2026-06-04 09:00:00"}
- {"session": "S103", "uid": "u004", "role": "user", "text": "我的邮箱是 zhangsan@example.com 别记下来啊！", "ts": "2026-06-04 16:00:00"}
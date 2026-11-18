# B 验证记录

此目录保存可复核的测试与模型运行记录。`.pytest/` 是独立测试的临时索引目录，不提交。
模型权重在 `models/embedding/`，合成语料的四组索引在 `data/b-fixtures/mock|real/`，均由脚本重建。
这些记录使用合成文本，不能充当 30 道正式题的评估结果。


## 当前英文版本

活动语料 `fixture-en-v2`，规则 `structure-offset-v2`。`tests.xml` 为独立验证环境的 78 项通过记录；`real-smoke.json` 和 `clean-real-smoke.json` 分别为项目环境与独立环境的英文真实模型验证，均为 12 次检索通过，并逐一检查返回片段的原文坐标。两者索引版本相同。

`frontend-smoke.json` 为浏览器验证记录，`debug-real-english.png` 与 `debug-mobile-english.png` 为英文正文的桌面/手机截图。`archive/zh-v1/` 保存替换前的中文语料和旧结果；这些历史记录中的版本与块数不代表当前活动语料。

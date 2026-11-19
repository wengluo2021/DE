# Digital Content and Services 原文对照复核

复核方式：AI 辅助原文复核。日期：2026-11-19。

本复核直接读取原始 HTML，用 `html.parser` 清点 `#document1` 中的主条文和序言节点，再按清洗 JSON 的 Python 区间 `[start, end)` 回切正文。没有打开浏览器做页面视觉检查。

## 输入与产物

| 文件 | SHA-256 | 字节数 |
| --- | --- | --- |
| `data/raw/Digital Content and Services.html` | `83b8ec2ad8d5a293c278fcffc5add389425bd7c688f92bf110d4ce2b929826f2` | 520093 |
| `data/processed/eu_digital_content_2019_770.txt` | `6e251e53b94cb4e793d9cd32889a0f70b7e62d7399eacc15197f37bb132ac3bf` | 118158 |
| `data/processed/eu_digital_content_2019_770.json` | `3d7b88ac3b35365986c18970dfc24cdf6b1574f701c13c350efe7466e5e366ab` | 409690 |
| `data/sources.json` | `d9edf17d3bf6748b66cdfa20a8ae9f6b2e45091d6fa88e826d28f5c5ff890aac` | 21962 |

正文 118079 个 Python 字符，只含 LF，文件以一个换行结束。

## 主条文与 DOM

`#document1` 内的 `div.eli-subdivision` 主条文为 `art_1` 至 `art_27`，共 27 个。没有 `cpt_` 章节，也没有 `anx_` 附件。序言节点为 `rct_1` 至 `rct_87`，共 87 个。正文脚注 23 条。清洗结果的条文编号、`chapter_id=null`、空章节、空附件、87 项序言和 23 条脚注与这次清点一致。

## 抽查

| 位置 | 区间 | 回切结果 |
| --- | --- | --- |
| 第 1 条 | `[78438, 79082)` | `Article 1` / `Subject matter and purpose` |
| 第 14 条 | `[99518, 102616)` | `Article 14` / `Remedies for lack of conformity` |
| 第 27 条 | `[113198, 113269)` | `Article 27` / `Addressees` |
| 列表 | `[100102, 100206)` | `(a) the value the digital content or digital service would have if there were no lack of conformity; and` |
| 脚注 | `[113395, 113426)` | `(1) OJ C 264, 20.7.2016, p. 57.` |
| 脚注引用 | `[516, 595)` | `Having regard to the opinion of the European Economic and Social Committee (1),` |

第 14 条保留 7 个列表项。脚注 `act:1` 的 `referenced_by` 指向上述序言块。

## 期限、例外与限制

- 第 11 条 `[94633, 96386)` 规定，如果成员国只让交易者对供给后一段时间内显现的不符承担责任，该期间不得短于供给后两年。短语从字符 95202 开始。
- 第 14 条允许消费者要求恢复符合性，除非恢复符合性不可能或费用不成比例。该限制从字符 99949 开始，位于第 14 条内。
- 第 24 条第 1 款规定 2021 年 7 月 1 日前完成转化，措施自 2022 年 1 月 1 日起适用。
- 第 24 条第 2 款规定指令适用于 2022 年 1 月 1 日起发生的供给，但第 19 条和第 20 条只适用于该日起订立的合同。该句从字符 112467 开始，位于第 24 条 `[111670, 112565)` 内。
- 第 26 条 `[113029, 113196)` 只规定公布后第 20 日生效，没有把 2022 年 1 月 1 日写成第二次生效。

## 全文覆盖

27 条主条文中，24 条在折叠空白后与 DOM 文本一致。第 3、23、26 条的差异来自比较器在标签两侧插入空格：脚注 `(21)`、公报链接 `(OJ L 136, 22.5.2019, p. 1)`，以及 `Union</span>.`。去掉这些标签边界空格后，三条文本一致。本文件没有附件，正文在最后一条脚注结束。

## 重复处理与异常检测

最终来源记录写入后连续两次清洗，txt 与 JSON 字节哈希都是上表中的值。

在临时副本中删除第 27 条后，校验退出码为 1，原因是主条文变为 1–26。删除全部主条文后，校验退出码为 1，原因是主条文列表为空。正式产物没有被这两次失败检查改写。

## 未纳入本文件的问题

本复核没有做浏览器视觉检查。页面链接的合并文本 `02019L0770-20190522` 不是本快照正文。

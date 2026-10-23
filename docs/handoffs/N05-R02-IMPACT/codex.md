# N05-R02-IMPACT：实际 G01 失败封存

结论：**N05-R02-IMPACT BLOCKED；官方 G01 本次真实执行 failed，当前不得作为有效前置。** 一次正式调用实际exit `1`，25/26检查通过；唯一失败 `P01-01-cmd1`。7必需命令全部由现行执行器执行，正确性断言、测试、锁、源码均未改变；未重跑本卡，未冒签成功，未签G02或开始P02-02。封存后停写。

最小阻塞 `N05-R02-ENV-NPM-01`：P01-01集成测试 `test_npm_ci_is_repeatable_and_lock_file_is_unchanged` 首轮 npm ci 使用本卡新空npm缓存，真实registry下载发生ECONNRESET，最终 `subprocess.TimeoutExpired`（900秒）；套件55passed/1failed，exit1。命令实际耗时约1027秒，原日志见 `artifacts/gates/G01-logs/P01-01-cmd1.log`。这是已确认的外部下载/缓存准备问题；当前没有证据据此认定业务源码缺陷。`.pytest_cache`拒绝访问只产生两个警告，不是此失败的根因。

环境准备遗漏：本轮只预先复制了旧N05独占uv缓存，没有预先复制已验证npm缓存。下载等待中在原900秒边界之后，按冻结package-lock的SHA512验证三包，使用npm自带cacache原子API补到本卡系统TEMP缓存；0额外网络请求，无全局配置、ACL或源码变更。没有改变正式Gate参数、重启命令或修改失败结果。随后正式P01-01-cmd3真实npm ci exit0（约6.6秒），说明必要缓存条件已发生变化；首轮失败仍原样保留。仅只读查询本任务进程树，没有结束任何进程，也未干预另一Android工程。

本轮独立影响审查及输入闭包已实证完成：真实auto候选 `content-sha256:477a883d2a29deb5cb60f8269c8712693d9e7aedeb3a620ba4953a630289158c`，82文件；完整dirty `content-sha256:eaea942624f00e5da16e89a3e744d3a2c1c659fcf9eeda0a23787116681d636f`。当前G00、三份预验收123输入/29命令日志及原Phase01交付有效；最新M01已改绑不可变历史G01。6个外部cwd `-I -B` 新进程通过六包/领域导出顺序/零第三方/未交付入口显式失败。新review184项保留全部10个活跃层源码和必需传递依赖，逐项说明旧262输入保留/移出；P02业务测试/当前文档/人工交接/业务日志未被用作bootstrap正确性证明。P02 evidence/seal仅因必需precheck的封存来源绑定保留，后继依赖刷新只能追加附件。原52项受控返工探针及冻结新环境安装证据仅按未变主体明确复用。

本次其它真实结果：P01-02套件96passed、P01-03套件74passed；剩余6必需命令全部exit0，5附加断言/14记录检查通过。正式阶段测试合计225passed/1failed，不能写226passed。官方40输入、review184输入、12原日志、G00依赖复算无漂移；新review为独立源码/证据影响approval，并不覆盖随后失败的必需命令及F4签收条件，不能把approved当G01通过。

- 官方失败G01 SHA256：`9f30bb45307721ecdb6d85259bac18230002d91d6dc5eabc61f55fd41337e35c`。
- 独立review SHA256：`e64827a62caa4c497304c66d85df154ac6047e571b3c5947b97a2d7c93925efc`。
- 正式实际运行原日志 SHA256：`82d568db53c42fa1e5029c10ad5cb8e65dea816ba3cec7611815b6f50cc2db78`；UTC `2026-10-05T08:45:59.180331+00:00` → `2026-10-05T09:05:02.249701+00:00`，exit `1`。
- G00 SHA256：`c5e57a6d250ff83f9ceed524f6219a3b1cb9474697a3354b5f102fe24c3bb7e4`，未改。
- 旧官方G01/review/12日志共14文件及历史marker授权/精确路由5文件，共19文件，覆盖前逐字节归档；路径/hash/bytes见 `archive-manifest.json`。
- 机器审计、全部命令计数、12原日志SHA和环境处置原始来源见 `final-audit.json` / `commands` / `environment`；封存见 `seal.json`。

工作根 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，无Git；独立原N05身份，模型/推理请求gpt-6.1-sol/xhigh，未参与实现、未加子审查。活跃脚本/UV/npm缓存/pytest/日志仅在本卡系统TEMP。未修改实现/测试/契约/锁/所有权/policy/G00/他人交接/state，无重置或购买。

恢复责任：root核验封存后，若专属npm缓存完整性与实际安装必要条件仍成立，再明确安排新的限定N05环境恢复任务；保留本次失败原字节，沿用同一正确性测试/冻结锁，再执行新的正式Gate。未授权本卡第二次实跑，不继续P02链。

限制：仅Phase01源码/导入/分层影响审查，未执行P02业务预验收；当前无有效G01，不授权下游。Node22/GitHub Actions及数据库/求解/仿真/模型/浏览器未实跑。执行器predecessor递归review缺口和global revision比较行为未改；后续相关源码/导入/层扫描输入变化仍需影响复核，无关未绑定元数据不机械使历史阶段失效。当前只有G01附加断言注册，后续阶段需另卡覆盖治理。

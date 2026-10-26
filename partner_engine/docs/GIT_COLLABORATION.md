# 双人 Git 协作 · 复制命令手册

适用：Windows PowerShell；甲方 DSH/Codex、乙方 PARTNER/Claude。2026-10-22 核查时本机 Git 为 2.55.0，合并工程尚无 Git 仓库。本文是操作说明，创建本文不会自动建仓、上传或邀请对方。

快速入口：[打开终端](#session) · [首次建仓](#initialize) · [对方克隆](#clone) · [开始任务](#new-task) · [提交上传](#upload) · [上传证据](#evidence) · [对方复验](#review) · [同步最新版](#sync) · [冲突处理](#conflicts) · [暂存工作](#stash) · [误操作恢复](#recovery) · [离线传递](#offline)

<a id="session"></a>

## 0. 每次打开终端先执行

进入自己的**运行工程根**。本机是下面目录；对方将引号内路径替换为自己的克隆目录。不要在父目录 DSH 骨架中执行。

```powershell
Set-Location 'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent\merged'
if (-not (Test-Path 'backend/app/contracts/common.py')) { throw '目录错误：请进入合并工程根' }
```

为方便整段复制，定义一个只作用于当前终端的 Git 包装函数：`gg` 等于执行 `git`，但任意非零退出都会立即停止当前代码块，避免上一步失败后仍上传。每个新终端重新定义；无需修改用户全局配置。

```powershell
function gg {
    & git @args
    if ($LASTEXITCODE -ne 0) { throw "Git 失败，退出码 $LASTEXITCODE。先处理错误，再继续。" }
}
function Assert-Clean {
    $gitGuideChanges = @(gg status --porcelain)
    if ($gitGuideChanges.Count -gt 0) { throw '存在未提交修改：先提交或按第9节暂存工作' }
}
```

已有仓库后检查：

```powershell
gg rev-parse --show-toplevel
gg status --short --branch
gg remote -v
```

始终遵守 [分工协议](../COLLABORATION_SPLIT_20261021.md) 和 OWNERSHIP.json。分支隔离不会自动解决公共契约冲突。公共契约仍由乙方串行集成。

<a id="initialize"></a>

## 1. 首次建立共享仓库（双方只选一人为初始化方）

先由双方确认共同基线。在 GitHub 网页创建**空的私有仓库**，不勾选 README/.gitignore/License，并邀请对方为协作者。记下 HTTPS 地址。GitHub 创建与邀请由网页完成，本文不假定已完成。

初始化方在工程根执行；已有 .git 时停止，不要重新建立另一套历史。

```powershell
if (Test-Path '.git') { throw '已有 Git，请直接进入日常流程' }
gg init -b main
$gitGuideName = Read-Host '输入你的提交署名'
$gitGuideEmail = Read-Host '输入提交邮箱（可用GitHub提供的私密邮箱）'
gg config --local user.name $gitGuideName
gg config --local user.email $gitGuideEmail
gg add .
gg diff --cached --stat
gg diff --cached
```

检查首次暂存的全部文件。现有规则忽略 .venv、node_modules、frontend/dist、.env 和普通日志；确认没有密码、密钥、本地数据库备份或误纳入的历史大文件。发现错误按第10节取消暂存。

确认后执行：

```powershell
gg commit -m '建立 R30-E 合并工程共同基线'
$gitGuideRemote = Read-Host '粘贴空私有仓库的HTTPS地址（不要包含令牌）'
gg remote add origin $gitGuideRemote
gg push -u origin main
```

身份验证使用 Git 弹出的登录流程。远端已有提交而推送被拒时，先核对远端；不要强推或直接合并无关历史。建议 main 设置必须通过 Pull Request、另一位协作者审批、禁止强推。

<a id="clone"></a>

## 2. 对方首次下载（在新目录操作）

保留原工作副本；新克隆目录不能是已有工程目录。下面两个输入填写仓库地址、新目录的绝对路径。

```powershell
$gitGuideRemote = Read-Host '粘贴共享仓库HTTPS地址'
$gitGuideClone = Read-Host '输入不存在的新克隆目录绝对路径'
if (Test-Path -LiteralPath $gitGuideClone) { throw '目标已存在，请使用新目录' }
gg clone $gitGuideRemote $gitGuideClone
Set-Location -LiteralPath $gitGuideClone
gg config --local user.name (Read-Host '输入你的提交署名')
gg config --local user.email (Read-Host '输入提交邮箱')
gg status --short --branch
```

按 [构建规范](DEVELOPMENT.md) 安装自己的依赖。未合入的旧代码放到新任务分支，逐文件比较移植；不要用整个旧文件夹覆盖克隆结果。两边各自 git init 再交换目录会产生无关历史。

<a id="new-task"></a>

## 3. 开始一个新任务

先保证当前修改已经提交或暂存工作。分支名只用英文小写、数字、斜线和连字符，例如 `dsh/r09-metrics-20261022`、`partner/r05-contracts-20261022`。不要复用已合并任务分支。

```powershell
Assert-Clean
gg switch main
gg pull --ff-only origin main
$gitGuideBranch = Read-Host '输入本次新分支名，例如 dsh/r09-metrics-20261022'
gg switch -c $gitGuideBranch
gg rev-parse HEAD
```

记录最后一行 SHA 作为任务起点。动手前阅读最新交接及文件所有权。

<a id="upload"></a>

## 4. 修改完成：验证、提交、上传

在当前任务分支操作。每次先查看，不要直接把所有人的修改一起提交：

```powershell
gg status --short
gg diff --stat
gg diff
```

更新交接文档后刷新文件清单，再运行统一验证。每次生成新的输出目录；该目录在工程外，不会自动上传。

```powershell
& .\.venv\Scripts\python.exe scripts/build_file_map.py
if ($LASTEXITCODE -ne 0) { throw '文件清单生成失败' }
$gitGuideEvidence = Join-Path '..\tmp' ('git-handoff-' + [guid]::NewGuid().ToString('N'))
& .\.venv\Scripts\python.exe scripts/verify_delivery.py --out-dir $gitGuideEvidence
$gitGuideVerifyExit = $LASTEXITCODE
Write-Host "验证退出码：$gitGuideVerifyExit；原始证据：$gitGuideEvidence"
```

查看 results.json 和失败日志。当前已登记的跨层导入仍可能导致整体非零，必须记录实际失败；上传供审查的代码不代表允许合入 main。数据库/模型与专项验收按任务另跑，统一脚本不替代它们。

**明确添加本任务文件。**下面是 R09 示例，其他任务修改为其真实路径；提交前补齐交接文档的准确文件名：

```powershell
gg add -- backend/app/evaluation backend/tests/evaluation FILE_MAP.md
$gitGuideHandoffFile = Read-Host '输入本次交接文档的仓库相对路径'
gg add -- $gitGuideHandoffFile
gg diff --cached --stat
gg diff --cached
```

确认暂存内容及验证结论后上传。上传前的守卫防止误推 main；首次及后续上传均可用此块。

```powershell
if ((gg branch --show-current) -eq 'main') { throw '请使用任务分支，不直接推main' }
$gitGuideMessage = Read-Host '输入本次提交说明'
gg commit -m $gitGuideMessage
gg push -u origin HEAD
gg rev-parse HEAD
```

已有提交且没有新修改、只需重试上传时，单独执行 `gg push -u origin HEAD`，无需再次 commit。记录推送成功的 SHA；本地 commit 成功但 push 失败，对方还看不到。

<a id="evidence"></a>

## 5. 一起上传测试日志与“最新记录”

交接至少写：任务、起点SHA、改动文件、契约版本、命令/退出码、结果、限制、待对方处理项。先提交待验代码，再记录其 SHA、运行验证，最后提交证据与记录；不要让文档引用“包含自身的最终提交SHA”。原始验证前后若改了业务源，需要重新验证受影响部分。

父目录 tmp 和本地 ZIP 不会自动同步；工程 .gitignore 也忽略 *.log。把选定且已脱敏的证据复制到工程内，以下块每次输入原始验证目录，目标使用随机新目录：

```powershell
$gitGuideSource = Read-Host '输入原始验证目录路径，例如 ../tmp/git-handoff-某个编号'
if (-not (Test-Path (Join-Path $gitGuideSource 'results.json'))) { throw '目录中缺少results.json' }
$gitGuideTarget = Join-Path 'docs/evidence' ([guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $gitGuideTarget -ErrorAction Stop | Out-Null
Copy-Item -LiteralPath (Join-Path $gitGuideSource 'results.json') -Destination $gitGuideTarget -ErrorAction Stop
Get-ChildItem -LiteralPath $gitGuideSource -Filter '*.log' -File | Copy-Item -Destination $gitGuideTarget -ErrorAction Stop
Write-Host "检查并脱敏后，再添加这个准确目录：$gitGuideTarget"
```

检查完成再执行下面一块。`-f` 仅用于该证据目录，不要使用 `git add -f .`。

```powershell
gg add -f -- $gitGuideTarget
& .\.venv\Scripts\python.exe scripts/build_file_map.py
if ($LASTEXITCODE -ne 0) { throw '文件清单生成失败' }
gg add -- FILE_MAP.md
gg diff --cached --stat
```

补齐交接的证据路径后按第4节提交上传。校验器 results.json 中有原始日志哈希；脱敏改动日志会改变哈希，必须保留原验证来源说明并另记发布副本的哈希，不能沿用旧哈希冒充一致。

<a id="review"></a>

## 6. 对方审查、运行任务分支、合并

作者在 GitHub 网页创建 Pull Request：base=main，compare=本任务分支，请另一人审查。PR 描述放改动、验证、阻塞及证据路径。

审查人在干净工作区下载对方分支。分支名输入 PR 中的准确名称：

```powershell
Assert-Clean
gg fetch origin
$gitGuideReviewBranch = Read-Host '输入待审查远端分支名'
gg switch --detach ('origin/' + $gitGuideReviewBranch)
gg log -1 --oneline
```

按第4节验证，核对文件范围及原始证据。此时为只读审查用途的 detached HEAD；需要修复时回作者任务分支，或从此建立新的修复分支，不在这里直接提交后离开。

通过后在 GitHub 合并 PR。失败则评论具体输入/预期/实际，由作者修复后再推同一分支。共享协议、数据库和缺失契约不得绕过评审。

<a id="sync"></a>

## 7. PR合并后，双方同步最新版

确保本地干净；使用 fresh main 开始下一个任务：

```powershell
Assert-Clean
gg switch main
gg pull --ff-only origin main
gg log -5 --oneline
gg rev-parse HEAD
```

双方 main 的 SHA 相同，才是同一已同步版本。若契约/锁文件变了，按构建规范重新安装或生成并检查；git pull 不会安装依赖。自动生成物应已由提交者随公共契约一起交付。

<a id="conflicts"></a>

## 8. 我开发期间，对方已经合并了新代码

在**自己的任务分支**、已提交且干净的状态执行。这里使用 merge 保留已共享历史，不要求强推：

```powershell
Assert-Clean
if ((gg branch --show-current) -eq 'main') { throw '当前是main，请切回自己的任务分支' }
gg fetch origin
gg merge --no-edit origin/main
```

成功后复跑受影响验证、更新交接，再 `gg push`。出现冲突时停在这里，按下一节处理。

### 合并冲突

查看冲突文件：

```powershell
gg status
gg diff --name-only --diff-filter=U
```

逐个打开文件，保留正确的双方改动，去掉 `<<<<<<<`、`=======`、`>>>>>>>` 标记。公共契约由乙方集成人裁定；FILE_MAP.md 按合并后的 OWNERSHIP 与实际文件重新生成；生成契约按 DEVELOPMENT.md 从源重生成。不盲选 ours/theirs。

修完后逐个输入处理好的文件名，重复添加直到全部处理：

```powershell
$gitGuideResolvedFile = Read-Host '输入已解决的冲突文件相对路径'
gg add -- $gitGuideResolvedFile
gg diff --name-only --diff-filter=U
```

最后一条无输出后，检查并完成合并：

```powershell
gg diff --cached --check
gg commit -m '合并main并解决任务分支冲突'
```

复跑验证后上传。若无法裁定，可在**merge尚未完成时**取消这次合并，返回合并前已提交的状态：

```powershell
gg merge --abort
gg status
```

<a id="stash"></a>

## 9. 有未完成修改，暂时要切换分支

stash 保存已跟踪和未跟踪文件，但 `-u` 不包含被忽略的 .env、日志等。忽略文件仍留在本机；需要备份的原始证据另行保存。

```powershell
gg stash push -u -m '临时保存：切换分支前的工作'
gg stash list
gg status --short
```

切回原来的任务分支并保证无其他修改，再查看 stash 编号、选择正确条目恢复。apply 保留备份，先不要 drop：

```powershell
gg stash list
$gitGuideStash = Read-Host '输入要恢复的条目，例如 stash@{0}'
gg stash apply $gitGuideStash
gg status
```

apply 冲突需逐文件处理；不要重复apply。确认内容完整且已提交后，可选择删除那个准确的 stash：`gg stash drop $gitGuideStash`。

<a id="recovery"></a>

## 10. 常见问题与恢复

### add错文件：取消暂存，保留本地修改

已有至少一个提交时：

```powershell
$gitGuideFile = Read-Host '输入需要取消暂存的文件相对路径'
gg restore --staged -- $gitGuideFile
gg status --short
```

首次提交前尚无 HEAD 时，先确认文件确实是新加入的，再用 `gg rm --cached -- $gitGuideFile`，该命令保留本地文件。

### 代码写错：已提交的修改用revert形成修正历史

先创建修复任务分支，确保工作区干净。下面仅针对**普通提交**；合并提交不能照搬，需由集成人判定保留哪条父线。

```powershell
Assert-Clean
gg log -10 --oneline
$gitGuideBadCommit = Read-Host '输入要撤销的普通提交SHA'
gg revert --no-edit $gitGuideBadCommit
```

验证后上传并走 PR。revert 也可能冲突；如需退出尚未完成的revert，执行 `gg revert --abort`。需要找回旧提交先看 `gg reflog`，记录SHA后请双方核对，不执行 reset --hard 或 clean -fd。

### 不小心在main开发了，但还没有提交

先查看状态，再从当前位置新建任务分支，修改会随工作区保留；然后按第4节提交：

```powershell
gg status --short --branch
$gitGuideRescueBranch = Read-Host '输入新的任务分支名'
gg switch -c $gitGuideRescueBranch
```

### main已产生本地提交，pull提示无法快进

先保存本地提交身份，再查看分歧。不要强推、不盲目在main合并：

```powershell
Assert-Clean
$gitGuideBackupBranch = Read-Host '输入新的保留分支名，例如 dsh/rescue-local-main'
gg switch -c $gitGuideBackupBranch
gg fetch origin
gg log --oneline --left-right origin/main...HEAD
```

需要的修改可在该分支经PR审查。待核对完成再恢复本地main；本文不提供覆盖历史的一键命令。

### push被拒绝（远端同名分支新增提交）

先确定双方确实在协作同一个任务分支，工作区干净后合并其远端版本：

```powershell
Assert-Clean
$gitGuideCurrentBranch = gg branch --show-current
if (-not $gitGuideCurrentBranch -or $gitGuideCurrentBranch -eq 'main') { throw '请在自己的任务分支操作' }
gg fetch origin
gg merge --no-edit ('origin/' + $gitGuideCurrentBranch)
```

解决冲突、验证、更新记录后再 `gg push`。若是仓库权限或登录失败，检查邀请和登录，不使用强推解决。

### 远端地址错误

```powershell
gg remote -v
$gitGuideRemote = Read-Host '输入双方确认的正确HTTPS地址'
gg remote set-url origin $gitGuideRemote
gg remote -v
```

没有origin时用 `gg remote add origin $gitGuideRemote`，不要重复add已有名称。遇到 TLS/证书报错不要关闭 sslVerify；检查系统时间、网络与证书配置。

### 对方说“没有看到最新代码或记录”

发送前查看：

```powershell
gg status --short --branch
gg log -3 --oneline
gg branch -vv
gg remote -v
```

核对是否只commit未push、推到了不同远端/任务分支、PR尚未合入、证据仍只在父目录tmp。对方需fetch对应分支；只有merge后pull main才会在main看到改动。

<a id="offline"></a>

## 11. 网络暂不可用：使用bundle传递已提交历史

仅在本次改动已提交后执行。bundle不包含未提交文件、依赖或被忽略日志。它是临时传递方式，最终仍要回到同一共享仓库。

发送方在工程根创建工程外的新文件：

```powershell
$gitGuideBundle = Join-Path (Split-Path (Get-Location).Path -Parent) ('handoff-' + [guid]::NewGuid().ToString('N') + '.bundle')
gg bundle create $gitGuideBundle --all
gg bundle verify $gitGuideBundle
Get-FileHash -LiteralPath $gitGuideBundle -Algorithm SHA256
```

接收方先比对发送的SHA256。在新目录首次接收可以 `git clone 文件路径 新目录`。已有共同历史的仓库中：

```powershell
$gitGuideBundle = Read-Host '输入收到的bundle绝对路径'
Get-FileHash -LiteralPath $gitGuideBundle -Algorithm SHA256
gg bundle verify $gitGuideBundle
gg bundle list-heads $gitGuideBundle
```

确认正确分支后，抓取为不覆盖已有分支的新名称：

```powershell
$gitGuideSourceBranch = Read-Host '输入bundle内的源分支名'
$gitGuideIncoming = 'incoming/' + [guid]::NewGuid().ToString('N')
gg fetch $gitGuideBundle ('refs/heads/' + $gitGuideSourceBranch + ':refs/heads/' + $gitGuideIncoming)
```

然后按第6节切到该分支审查，再由集成人合并；不要整体覆盖工作目录。

<a id="checklist"></a>

## 12. 上传前最后核对

任务分支、所有权、契约生成物、锁文件、交接记录与原始证据齐全；验证失败如实记录；push成功并给出SHA/PR地址；对方复验后合并。Git同步代码历史，独立验收仍需执行 [构建规则](DEVELOPMENT.md) 和具体任务要求。

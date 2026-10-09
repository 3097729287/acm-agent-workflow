# TB 排行榜服务

TB 的题目、代码、草稿、每日任务和经验值保存在本机。排行榜使用这份 Cloudflare Workers + D1 服务，统一保存每个安装用户的昵称、唯一 ID，以及首次本地审核通过的题目摘要。

程序首次运行生成 UUID 和随机凭据；更新版本沿用原身份。安装包不包含任何用户身份、凭据或个人数据库。修改昵称不会改变 ID。复制个人数据库到另一台机器会沿用同一身份；完整卸载并删除个人数据后会创建新身份。

日榜按北京时间当天计算，周榜从北京时间星期一开始，总榜统计全部不同题目。同题重复通过、运行和样例通过均不增加排名。界面展示 `昵称 #完整 ID`。客户端报告本地审核通过记录，服务暂不提供防作弊认证，也不将这类记录称为原站通过。

## 配置并发布服务

需要一个 Cloudflare 账号。免费额度是否够用取决于实际请求和数据库用量；费用与限额请查 [Workers 定价](https://developers.cloudflare.com/workers/platform/pricing/) 和 [D1 定价](https://developers.cloudflare.com/d1/platform/pricing/)。这份源码尚未绑定 Cloudflare 账号或真实数据库。

在此目录运行下面的命令：

```powershell
npm.cmd install
npx.cmd wrangler login
npx.cmd wrangler d1 create tb-leaderboard
```

将创建结果的 `database_id` 填入 `wrangler.jsonc`，替换 `REPLACE_WITH_CREATED_D1_DATABASE_ID`。部署前执行迁移并发布：

```powershell
npx.cmd wrangler d1 migrations apply tb-leaderboard --remote
npx.cmd wrangler secret put RATE_LIMIT_SALT
npx.cmd wrangler deploy
```

`RATE_LIMIT_SALT` 填入随机字符串，仅由服务器保管。Cloudflare 的登录信息和 API Token 不得放入桌面安装包。默认按 IP 限制新注册数、按身份限制每分钟请求；可通过配置中的限额调整。

将发布得到的 HTTPS 根地址填入 TB 的排行榜设置，例如 `https://tb-leaderboard.example.workers.dev`。软件自动注册身份、同步历史首次通过，并在新的本地审核通过后同步。服务连接失败时保留本机记录，稍后重试。公共分发也可将这个地址写入桌面程序旁的 `leaderboard.defaults.json`：

```json
{"endpoint":"https://tb-leaderboard.example.workers.dev"}
```

这个文件只存公共地址。未配置地址时，软件显示“排行榜服务尚未配置”，不显示虚构用户。

## 服务接口

除了 `GET /v1/health`，请求均携带 `X-TB-User: UUID` 和 `Authorization: Bearer 安装凭据`。凭据由客户端首次运行生成，服务器只保存其 SHA-256 摘要。请求体仅接受规定字段，最多 64 KiB。

| 接口 | 请求 | 返回 |
|---|---|---|
| `POST /v1/profile/register` | `{userId,nickname}` | `{userId,nickname,createdAt}`；重复注册验证原凭据 |
| `GET /v1/profile` | 无 | 当前身份与昵称 |
| `PUT /v1/profile` | `{nickname}` | 更新自己的昵称 |
| `POST /v1/events` | `{events:[{eventId,problemKey,acceptedAt,difficulty,scope:"local-reviewed"}]}` | `{processed,scope,notice}` |
| `GET /v1/leaderboard?period=daily` | 周期 `daily`、`weekly` 或 `total` | `{period,date,timezone,entries,self,notice}` |

每批最多 100 条通过记录。`problemKey` 是原题规范化链接的 SHA-256 摘要；`eventId` 是身份和原题摘要的 SHA-256 摘要。不发送题目代码、草稿、测试数据、翻译 API Key、原站 Cookie 或密码。记录按用户和原题唯一，重传不会增加题数；异步评测导致更早的通过记录稍后到达时，服务修正到更早日期。

本机接口为 `GET/POST /api/profile`、`GET /api/leaderboard?period=daily`、`POST /api/leaderboard/sync`、`GET /api/daily-tasks` 和 `POST /api/daily-tasks/claim`。每日任务领取与奖励保存在本机 SQLite 事务中，不依赖服务器。

## 本地验证

需要 Node.js 24 或更新版本。以下测试执行生产 Worker 处理器和真实 SQLite 查询，并测试身份保护、并发领取、跨日统计、重传、错误数据和真实 HTTP 客户端协议：

```powershell
node --test tests/worker.test.mjs
```

在 `tb_web` 目录验证桌面客户端：

```powershell
python -m unittest test_v5_services
```

Cloudflare 本地运行可使用 `npx.cmd wrangler d1 migrations apply tb-leaderboard --local` 和 `npx.cmd wrangler dev`。开发时仅回环地址允许 HTTP；公开服务必须用 HTTPS。生产服务仍需在账号配置后实际部署验证。

数据库迁移和事务调用采用 Cloudflare 官方 [D1 Worker API](https://developers.cloudflare.com/d1/worker-api/d1-database/) 与 [迁移命令](https://developers.cloudflare.com/d1/reference/migrations/)。

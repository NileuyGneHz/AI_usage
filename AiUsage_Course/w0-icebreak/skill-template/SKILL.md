---
name: ros2-topic-alive-check
description: 判断某个 ROS 2 话题当前是否真的在发数据。典型症状：节点明明在跑但下游收不到消息、ros2 topic echo 无输出、ros2 topic hz 显示 0 或直接挂住、话题在 list 里但 rqt 里没曲线。适用于排查"话题存在但没数据"这一类问题，不适用于节点根本没起来的排查。
---

# 判断话题到底有没有在发数据

四步，按顺序走，**每一步都能排除掉一类原因**，别跳步。

## 1. 话题注册了没有

```bash
ros2 topic list | grep <topic_name>
```

不在列表里 = 发布者节点根本没创建 publisher，去查上游节点的启动与命名空间（`/<ns>/<topic>` 常见于 launch 里加了 namespace）。

## 2. 有没有发布者

```bash
ros2 topic info <topic_name> -v
```

看 `Publisher count`：
- 0 → 上游节点起来了但没建 publisher，或建在了别的话题名上
- ≥1 → 继续下一步

同时看 QoS。**发布端 RELIABLE + 订阅端 BEST_EFFORT 是兼容的，反过来不兼容**，这是"echo 得到但程序收不到"的最常见原因。

## 3. 有没有实际数据流

```bash
timeout 3 ros2 topic hz <topic_name>
```

- 有频率输出 → 发布端正常，问题在订阅端（第 4 步）
- 无输出但第 2 步有 publisher → **"注册但无数据"**，通常是回调里阻塞、定时器没起、或消息在但被过滤

## 4. 订阅端问题定位

如果第 3 步频率正常但你的程序收不到：

- 检查订阅的 QoS durability：发布端 `TRANSIENT_LOCAL` 才能让**后启动**的订阅者收到历史消息
- 检查回调是否被 executor 饿死（单线程 executor 里有个长阻塞回调，其他话题全停）
- 用 `ros2 topic echo` 对照：echo 能收到而你收不到 → 100% 是 QoS 或命名空间，不是数据链路

## 结论速查

| 现象 | 结论 |
|---|---|
| list 里没有 | 上游没创建 publisher |
| info 里 publisher=0 | 上游节点没起来 / 名字不一致 |
| hz 无输出但 publisher≥1 | 回调阻塞或定时器没起 |
| hz 正常但程序收不到 | QoS 不兼容 / executor 饿死 / 命名空间错 |

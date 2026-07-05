from __future__ import annotations

from random import choice


def pick(lines: tuple[str, ...]) -> str:
    return choice(lines)


WEEKLY_OPENERS_CURRENT = (
    "这周群里已经有点动静了，有人在往上冲，也有人在稳定出洋相。",
    "这周目前不算安静，能狠狠干的在狠狠干，能掉链子的也没闲着。",
    "这周群里已经开始分层了，有人往前冲，有人忙着给周报提供素材。",
)

WEEKLY_OPENERS_SETTLED = (
    "上周这群玩得还挺实在，有人狠狠干得顺风顺水，有人狠狠干上头，还有人一整周基本都在给别人垫节目效果。",
    "上周群里不算消停，赢的人赢得很直接，倒霉的人也倒霉得挺完整。",
    "上周这群里该上头的上头了，该吃亏的也确实没少吃。",
)

WEEKLY_CLOSERS = (
    "总结一下：上周赢家赢得很直接，倒霉的人也倒霉得很完整，这周报基本没冤枉谁。",
    "总结一下：有人把这周玩明白了，也有人主要负责让周报别太无聊。",
    "总的来说，这周谁体面谁难看，基本都已经写在这了。",
)

QUERY_SELF_LOW = (
    "你现在 {length}cm，先别急着吹。",
    "你现在 {length}cm，排面还没攒起来。",
)

QUERY_SELF_MID = (
    "你现在 {length}cm，勉强算能看。",
    "你现在 {length}cm，混日子够了，但也别太有自信。",
)

QUERY_SELF_HIGH = (
    "你现在 {length}cm，难怪别人看你不顺眼。",
    "你现在 {length}cm，这数摆出来就挺招人烦。",
)

QUERY_TARGET_LOW = (
    "TA现在 {length}cm，排面还没攒出来。",
    "TA现在 {length}cm，基本还在起步阶段。",
)

QUERY_TARGET_MID = (
    "TA现在 {length}cm，混得过去。",
    "TA现在 {length}cm，不算丢人，但也没多强。",
)

QUERY_TARGET_HIGH = (
    "TA现在 {length}cm，难怪你专门来查。",
    "TA现在 {length}cm，怪不得容易招人惦记。",
)

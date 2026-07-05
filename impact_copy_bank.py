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

QUERY_LOW = (
    "你现在是 {length}cm，说有也算有。",
    "你现在 {length}cm，暂时还没什么排面。",
)

QUERY_MID = (
    "你现在 {length}cm，混日子是够了。",
    "你现在 {length}cm，不算难看，但也别太急着装。",
)

QUERY_HIGH = (
    "你现在 {length}cm，已经有点让人看着不爽了。",
    "你现在 {length}cm，位置摆在这，别人多少会有点烦。",
)

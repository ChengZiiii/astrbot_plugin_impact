from __future__ import annotations


COMMAND_ALIASES = {
    "rank": ("牛子排行", "牛牛排行", "长度排行", "排行", "jj排行榜", "jj排名", "jj榜单", "jjrank"),
    "toggle": ("开始银趴", "关闭银趴", "开启淫趴", "禁止淫趴", "开启银趴", "禁止银趴"),
    "yinpa": ("日群友", "透群友", "日群主", "透群主", "日管理", "透管理"),
    "inject": ("注入查询", "摄入查询", "射入查询"),
    "weekly_report": ("本周周报", "周报", "本周榜", "周榜"),
    "last_weekly_report": ("上周周报",),
    "weekly_stats": ("我的本周数据", "我的周数据"),
    "rival": ("我的恩怨簿", "我的宿敌", "恩怨"),
    "honor": ("群荣誉墙", "群荣誉", "荣誉墙"),
    "fuck_wife": ("日老婆", "透老婆"),
}

COMMAND_GROUP_MAP = {
    "dajiao": ("打胶", "开导"),
    "suo": ("嗦牛子",),
    "query": ("查询",),
    "pk": ("pk", "对决"),
    "rank": COMMAND_ALIASES["rank"],
    "toggle": COMMAND_ALIASES["toggle"],
    "yinpa": COMMAND_ALIASES["yinpa"],
    "inject": COMMAND_ALIASES["inject"],
    "weekly_report": COMMAND_ALIASES["weekly_report"],
    "last_weekly_report": COMMAND_ALIASES["last_weekly_report"],
    "weekly_stats": COMMAND_ALIASES["weekly_stats"],
    "rival": COMMAND_ALIASES["rival"],
    "honor": COMMAND_ALIASES["honor"],
    "fuck_wife": COMMAND_ALIASES["fuck_wife"],
    "help": ("淫趴介绍",),
}

USAGE_TEXT = """指令1: 嗦牛子 (给目标牛牛增加长度, 自己或者他人, 通过艾特选择对象, 没有at时目标是自己)
指令2: 打胶 | 开导 (给自己牛牛增加长度)
指令3: pk | 对决 (普通的pk, 单纯的random实现输赢, 胜利方获取败方随机数/2的牛牛长度)
指令4: 查询 (目标牛牛长度, 自己或者他人, 通过艾特选择对象, 没有at时目标是自己)
指令5: 牛子排行 | jj排行榜 | jj排名 | jj榜单 | jjrank (输出倒数五位和前五位, 以及自己的排名)
指令6: 开始银趴 | 关闭银趴 | 开启淫趴 | 禁止淫趴 | 开启银趴 | 禁止银趴 (由管理员或群主开启或者关闭)
指令7: 日群友 | 透群友 | 日群主 | 透群主 | 日管理 | 透管理 (当使用透群友的时候如果at了人那么直接指定)
指令8: 注入查询 | 摄入查询 | 射入查询 (查询目标被透注入的量，后接历史或全部可查看总量)
指令9: 本周周报 | 周报 (查看当前周实时周报)
指令10: 上周周报 (查看最近一次已结算的上周周报)
指令11: 我的本周数据 (查看你在本群当前周的详细数据)
指令12: 我的恩怨簿 | 我的宿敌 | 恩怨 (查看你在本群当前周的复仇目标和宿敌)
指令13: 群荣誉墙 | 群荣誉 | 荣誉墙 (查看本群最近几周的荣誉墙)
指令14: 日老婆 | 透老婆 (与老婆亲密互动，也可能NTR别人的老婆)
指令15: 淫趴介绍 (输出淫趴插件的命令列表)"""

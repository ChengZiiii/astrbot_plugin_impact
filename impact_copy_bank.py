from __future__ import annotations

from random import choice


def pick(lines: tuple[str, ...]) -> str:
    return choice(lines)


# ── 打胶结果 ──────────────────────────────────────────────

DAJIAO_GROWTH = (
    "手感在线！{jj}支棱起来了，+{delta}cm，今天状态拉满。",
    "涨了{delta}cm。{jj}今天争气了，继续保持别掉链子。",
    "稳了，+{delta}cm。{jj}终于干了件正经事。",
    "这把可以，{jj}涨了{delta}cm，没白忙活。",
)

DAJIAO_SHRINK = (
    "翻车了。{jj}掉了{delta}cm，今天是来搞笑的吧。",
    "-{delta}cm。{jj}今天罢工了，建议检查一下。",
    "亏了{delta}cm。这把操作，{jj}看了都摇头。",
    "掉了{delta}cm。{jj}：今天不在状态，勿cue。",
)

# ── 嗦牛子结果 ────────────────────────────────────────────

SUO_GROWTH = (
    "这口嗦得好，{jj}长了{delta}cm，嘴巴功夫到位了。",
    "涨了{delta}cm。看来你这嘴开过光。",
    "+{delta}cm。这口下去，{jj}直接起飞。",
)

SUO_SHRINK = (
    "嗦歪了，{jj}掉了{delta}cm。嘴瓢了吧。",
    "-{delta}cm。这口下去，{jj}直接缩水。下次瞄准点。",
    "亏了{delta}cm。嘴是好嘴，就是方向不太对。",
)

# ── PK结果 ────────────────────────────────────────────────

PK_WIN_POSITIVE = (
    "KO！{jj}加了{delta}cm，对面直接躺平，血赚。",
    "赢了！+{delta}cm到手。对面今天就是来送的。",
    "这把你赢，{jj}涨了{delta}cm。对面：？？？",
)

PK_WIN_NEGATIVE = (
    "赢是赢了，但赢得不好看。你掉了{delta}cm，对面也掉了，属于互殴。",
    "惨胜。你和对面一起掉，{jj}今天谁都没讨到好。",
    "赢了，但也没赢多少。{jj}掉了{delta}cm，对面也没好到哪去。",
)

PK_LOSE_NEGATIVE = (
    "被暴打了。{jj}掉了{delta}cm，对面反而涨了。脸呢？",
    "输了，-{delta}cm。对面加了，你掉了。这差距，不忍看。",
    "被按在地上摩擦。{jj}掉了{delta}cm，对面还在笑。",
)

PK_LOSE_BOTH = (
    "输了，而且输得不体面。你掉了{delta}cm，对面也没好到哪去。两个菜鸡互啄。",
    "你没赢，场面也没多体面。{jj}掉了{delta}cm，对面也掉了。",
    "这把谁都没赢。你掉了{delta}cm，对面也掉了，双输。",
)

# ── 银趴前奏 ──────────────────────────────────────────────

YINPA_PREFACE = (
    "来活了！{target}，{sender}已经就位，你准备好了吗？",
    "{sender}盯上了{target}。各位，好戏开场了。",
    "点名{target}！{sender}，该你表演了，别让观众失望。",
    "{sender}对{target}发起了冲锋。围观群众请就座。",
    "气氛到位了。{sender}，{target}，你俩上吧，我们看着。",
)

# ── 银趴结果 ──────────────────────────────────────────────

YINPA_RESULT_T = {
    1: [
        "{sender}那{length}cm的小牙签忙活了{duration}秒，{target}勉强收到{volume}ml。今日{target}累计：{total}ml。",
        "{sender}才{length}cm还想日{target}，忙活了{duration}秒挤出{volume}ml。今日战绩：{total}ml。",
        "{sender}用仅有的{length}cm折腾了{duration}秒，{target}获得{volume}ml。今日累计：{total}ml。",
    ],
    2: [
        "{sender}花了{duration}秒，给{target}灌了{volume}毫升。{target}今天已经吃了{total}毫升。",
        "{sender}磨蹭了{duration}秒，{target}收获{volume}毫升。今日累计：{total}毫升。",
        "{sender}操作了{duration}秒，{target}被注入{volume}毫升。今日战绩：{total}毫升。",
    ],
    3: [
        "{sender}那{length}cm让{target}有点招架不住，{duration}秒后射了{volume}ml。今日战绩：{total}ml。",
        "{sender}用{length}cm好好招待了{target}一番，{duration}秒灌了{volume}ml。今日累计：{total}ml。",
        "{sender}{length}cm冲刺了{duration}秒，{target}被灌了{volume}ml。今日战绩：{total}ml。",
    ],
    4: [
        "{sender}那{length}cm把{target}干到腿软，{duration}秒灌了{volume}ml。今日累计：{total}ml。",
        "{sender}仗着{length}cm狠狠教训了{target}，{duration}秒注入{volume}ml。今日战绩：{total}ml。",
        "{sender}的{length}cm让{target}欲仙欲死，{duration}秒收获{volume}ml。今日累计：{total}ml。",
    ],
    5: [
        "{sender}的{length}cm怪物级凶器让{target}直接昏了过去，{duration}秒灌了{volume}ml。今日战绩：{total}ml。",
        "{sender}用{length}cm巨物把{target}干到翻白眼，{duration}秒注入{volume}ml。今日累计：{total}ml。",
        "{sender}那{length}cm不是{target}能承受的，{duration}秒后{target}已经说不出话了……{volume}ml。今日战绩：{total}ml。",
    ],
}

# ── 查询分级 ──────────────────────────────────────────────

# ── 查长度结果 ──────────────────────────────────────
# charm_tier: 1=嫌短, 2=还行, 3=不错, 4=很大, 5=怪物
QUERY_SELF_T = {
    1: (
        "你才{length}cm？还没发育好吧，赶紧去补补。",
        "{length}cm。你这也太短了，让人笑话。",
        "{length}cm……这么小你也好意思查？",
    ),
    2: (
        "你才{length}cm？建议先去挂个号。",
        "{length}cm……这数据说出来有点丢人。",
        "{length}cm。别急，垫底也是一种体验。",
    ),
    3: (
        "{length}cm，及格线附近徘徊。继续努力。",
        "{length}cm，不上不下，属于中庸之道。",
        "{length}cm。一般般，不好不坏，看你后面能不能冲。",
    ),
    4: (
        "{length}cm。难怪这么招摇，确实有资本。",
        "{length}cm……这已经不是正常范围了吧？",
        "{length}cm。牛。这数据摆出来，谁看了不嫉妒。",
    ),
    5: (
        "{length}cm？你是人类吗？这已经不是正常范畴了。",
        "{length}cm——建议你不要随便让别人知道，会被当怪物。",
        "{length}cm。你老婆还好吗？",
    ),
}
QUERY_TARGET_T = {
    1: (
        "TA才{length}cm。还没发育好，建议捐款。",
        "TA {length}cm。这么小，你查来干嘛？",
        "TA {length}cm……这么短，不忍直视。",
    ),
    2: (
        "TA才{length}cm。你查这个干嘛，没什么好看的。",
        "TA {length}cm。还在起步阶段，别对TA期望太高。",
        "TA {length}cm……你确定要和这个比？",
    ),
    3: (
        "TA {length}cm，中规中矩，没什么好炫耀的。",
        "TA {length}cm，还行吧，不算丢人。",
        "TA {length}cm。不上不下，和你半斤八两。",
    ),
    4: (
        "TA {length}cm。难怪你专门来查，确实有点东西。",
        "TA {length}cm……这数据，说实话有点离谱。",
        "TA {length}cm。你确定要和这个比？勇气可嘉。",
    ),
    5: (
        "TA {length}cm。这已经不是人类范畴了，你在查什么怪物。",
        "TA {length}cm。建议不要和TA比，你会自闭的。",
        "TA {length}cm……这是什么神仙数据？你认真的？",
    ),
}

# ── 周报开头 ──────────────────────────────────────────────

WEEKLY_OPENERS_CURRENT = (
    "这周群里已经炸开锅了。有人在往上冲，有人在原地摆烂。",
    "这周群里分层了。能干的在猛干，不能干的在提供节目效果。",
    "这周群里不太平。有人风光，有人丢人，周报有的写了。",
)

WEEKLY_OPENERS_SETTLED = (
    "上周这群人玩得挺疯。赢的人赢得很直接，输的人输得很彻底。",
    "上周群里很精彩。有人风光无限，有人全程陪跑。",
    "上周这群里该上头的上头了，该吃亏的一个没落下。",
)

# ── 周报结尾 ──────────────────────────────────────────────

WEEKLY_CLOSERS = (
    "总结：上周赢家赢得很直接，倒霉的人也倒霉得很完整。周报没冤枉谁。",
    "总结：有人把这周玩明白了，也有人主要负责让周报别太无聊。",
    "总的来说，这周谁体面谁难看，全写在这了。不服下周继续。",
)

# ── 冷却提示 ──────────────────────────────────────────────

COOLDOWN_DAJIAO = (
    "刚打完，{jj}不需要休息的吗？{cd}秒后再来。",
    "急什么，{jj}刚用完。{cd}秒后再说。",
    "你的{jj}刚经历过一轮，让它喘口气。{cd}秒。",
)

COOLDOWN_SUO = (
    "刚嗦过，嘴也要歇会。{cd}秒后再来。",
    "嘴速太快了，歇一下。{cd}秒。",
    "刚嗦完就又来？{cd}秒后再试。",
)

COOLDOWN_PK = (
    "刚打完一场，脸还没消肿呢。{cd}秒后再来。",
    "急什么，上一场的伤还没好。{cd}秒。",
    "连续打 pk 你不要命了？{cd}秒后再来。",
)

COOLDOWN_YINPA = (
    "刚结束，你这体力也太差了。{cd}秒后再来。",
    "喘口气吧你。{cd}秒。",
    "刚搞完就又来？{cd}秒后再说。",
)

COOLDOWN_FUCK_WIFE = (
    "刚完事，歇会儿吧。{cd}秒后再来。",
    "你这体力不行啊，{cd}秒后再来。",
    "刚交完公粮就又来？{cd}秒后再说。",
)

# ── 其他杂项 ──────────────────────────────────────────────

NEW_USER_REPLY = (
    "你还没建档，先给你补个{length}cm的起步款。别嫌少，后面全靠自己。",
    "档案不在？给你补一个{length}cm的。起步阶段，别急。",
)

TOGGLE_ON = (
    "开了，想玩就继续造。",
    "银趴已开启，各位准备好了吗。",
)

TOGGLE_OFF = (
    "关了，今天到此为止。",
    "银趴已关闭，各位洗洗睡吧。",
)

PK_NO_TARGET = (
    "没@人打什么pk，先找好对手。",
    "打pk不@人？你在空气斗智斗勇吗。",
)

PK_SELF_TARGET = (
    "打自己？你是想图什么。自虐癖？",
    "别对自己下手，留点面子。",
)

PRIVATE_WEEKLY = (
    "周报去群里看，私聊里没这些热闹。",
    "私聊看什么周报，去群里凑热闹。",
)

DISABLED_COMMAND = (
    "这个命令现在没开，别试了。",
    "此功能已关闭，省省吧。",
)

DISABLED_GROUP = (
    "当前群已被插件黑名单禁用。",
    "这个群被禁用了，换群玩。",
)

WHITELIST_GROUP = (
    "当前群不在插件白名单中。",
    "这个群不在白名单里，玩不了。",
)

NO_DATA_RANK = (
    "目前记录的数据量小于{min}，凑不出像样的排行。",
    "人太少，排行排不出来。至少要{min}个人。",
)

NO_DATA_WEEKLY = (
    "这周还没闹出什么动静，暂时还写不出什么像样的周报。",
    "本周零数据，周报写不了。",
)

NO_LAST_WEEKLY = (
    "还没有能翻的上周周报，之前那点事还没攒出来。",
    "上周周报？不存在的，之前没数据。",
)

NO_RIVAL = (
    "你这周还没和谁结下梁子。",
    "这周你太平了，没结下任何仇家。",
)

NO_HONOR = (
    "本群现在还攒不出荣誉墙，再玩几轮。",
    "荣誉墙空的，再努努力。",
)

NO_WEEKLY_STATS = (
    "你这周在本群还没什么数据可看。",
    "本周你啥也没干，没数据。",
)

YINPA_SELF_TARGET = (
    "你连自己都不放过，是今天真没别的活人了？",
    "对自己下手？你这口味也太重了。",
)

YINPA_NO_MEMBERS = (
    "这边拉不到群成员列表，这次没法随机点人。",
    "群成员列表拉不到，随机不了。",
)

YINPA_NO_TARGET = (
    "这次没翻到合适的目标。",
    "没抽到人，运气不太好。",
)

TOGGLE_ADMIN_ONLY = (
    "这开关得管理员或群主来动。",
    "不好意思，这开关你动不了。",
)

INJECTION_TODAY = (
    "{object}当日总被注射量为{volume}ml。",
    "{object}今天被灌了{volume}ml，还行吧。",
)

INJECTION_HISTORY = (
    "{object}历史总被注射量为{volume}ml。",
    "{object}累计被注入{volume}ml，铁打的身子。",
)

# ── 日老婆结果 ──────────────────────────────────────────────
# charm_tier: 1=小牙签, 2=普通, 3=凶器, 4=巨炮, 5=怪物
FUCK_WIFE_SELF = {
    1: [
        "{name}低头看了看你{length}cm的小牙签，叹了口气：'就这？'你委屈地塞了{vol}ml。今日她已被注入{dvol}ml（{dcnt}次）。",
        "你趴在{name}身上忙活半天，她打了个哈欠：'你那{length}cm小牙签就完了？'{vol}ml，也就这样了。今日她已被注入{dvol}ml（{dcnt}次）。",
        "{name}皱了皱眉：'你{length}cm的小牙签是不是没吃饭……'你委屈地射了{vol}ml，她一脸嫌弃。今日她已被注入{dvol}ml（{dcnt}次）。",
    ],
    2: [
        "你把{name}按在身下，{length}cm顶了进去……她脸红着小声说'主人……轻点……'这次塞进了{vol}ml。今日她已被注入{dvol}ml（{dcnt}次）。",
        "你搂住{name}的腰，{length}cm缓缓送入，她喘息着说'嗯……好舒服……'射了{vol}ml进去。今日她已被注入{dvol}ml（{dcnt}次）。",
        "{name}被你{length}cm压在墙上，{vol}ml一股脑全灌进去了，她腿都软了。今日她已被注入{dvol}ml（{dcnt}次）。",
    ],
    3: [
        "{name}被你{length}cm的大炮弄得浑身发抖，带着哭腔喊'不行了不行了……'你一股脑灌了{vol}ml进去。今日她已被注入{dvol}ml（{dcnt}次）。",
        "你按住{name}的腰用{length}cm凶器狠狠冲刺，她尖叫着瘫软在床上，{vol}ml全收下了。今日她已被注入{dvol}ml（{dcnt}次）。",
        "{name}被你{length}cm大炮干得翻着白眼，断断续续地说'要……要死了……'一股脑灌了{vol}ml进去。今日她已被注入{dvol}ml（{dcnt}次）。",
    ],
    4: [
        "{name}被你{length}cm的巨炮干到眼神失焦，嘴角流着口水喃喃'坏掉了……'，{vol}ml灌满了她。今日她已被注入{dvol}ml（{dcnt}次）。",
        "你粗暴地用{length}cm巨物贯穿{name}，她抽搐着高潮了一次又一次，{vol}ml全射了进去。今日她已被注入{dvol}ml（{dcnt}次）。",
        "{name}已经说不出话，{length}cm巨炮还在往里顶，{vol}ml把她灌得小腹微隆。今日她已被注入{dvol}ml（{dcnt}次）。",
    ],
    5: [
        "{name}被你{length}cm的怪物级凶器干晕了过去，你还在继续……她醒来时发现自己已经被灌了{vol}ml。今日她已被注入{dvol}ml（{dcnt}次）。",
        "你{length}cm的神兵过于庞大，{name}直接昏死过去，你只好自己动……{vol}ml一滴不漏。今日她已被注入{dvol}ml（{dcnt}次）。",
        "{name}被你{length}cm擎天柱干得翻着白眼吐着舌头，意识已经飞走，{vol}ml全灌了进去。今日她已被注入{dvol}ml（{dcnt}次）。",
    ],
}
FUCK_WIFE_NTR = {
    1: [
        "你掏出{length}cm的小牙签，{name}就笑出了声：'就这尺寸也敢来？'你脸一红射了{vol}ml。今日她已被注入{dvol}ml（{dcnt}次）。",
        "{name}看了一眼你{length}cm的小牙签，嫌弃地说'还不如我老公'，勉强让你塞了{vol}ml。今日她已被注入{dvol}ml（{dcnt}次）。",
        "你忙活半天{name}毫无波澜——你那{length}cm小牙签她根本没感觉，她甚至在看手机：'完了？那我走了。'{vol}ml，太丢人了。今日她已被注入{dvol}ml（{dcnt}次）。",
    ],
    2: [
        "{name}本来是{cuckold}的老婆，现在被你的{length}cm干得在你身下求饶……{vol}ml 全给了她。今日她已被注入{dvol}ml（{dcnt}次）。",
        "你趁{cuckold}不在，{length}cm把{name}按在沙发上……{vol}ml 注入完毕，她咬着嘴唇说不出话。今日她已被注入{dvol}ml（{dcnt}次）。",
        "{name}的老公{cuckold}还不知道，你正用{length}cm灌她，{vol}ml已经进去了……今日她已被注入{dvol}ml（{dcnt}次）。",
    ],
    3: [
        "你{length}cm的大炮把{name}干得语无伦次，她一边喊{cuckold}的名字一边夹紧你……{vol}ml一滴不漏。今日她已被注入{dvol}ml（{dcnt}次）。",
        "{name}被你{length}cm凶器吓到了，咬着被子不敢叫出声，被你灌了{vol}ml后瘫在床上起不来。今日她已被注入{dvol}ml（{dcnt}次）。",
        "{name}翻着白眼，你{length}cm大炮还在往里送，她断断续续地说'要被你日死了……'，你{vol}ml全灌了进去。今日她已被注入{dvol}ml（{dcnt}次）。",
    ],
    4: [
        "你干得{cuckold}的老婆{name}两眼翻白，{length}cm巨炮全根没入，她痉挛着夹紧你，{vol}ml全灌了进去。今日她已被注入{dvol}ml（{dcnt}次）。",
        "趁{cuckold}不在你把{name}按在床上，{length}cm巨物干到失禁，她咬着拳头不敢出声，{vol}ml一滴没漏。今日她已被注入{dvol}ml（{dcnt}次）。",
        "{name}在你{length}cm巨炮下抽搐着高潮，{cuckold}的绿帽已经戴稳了……{vol}ml全给了她。今日她已被注入{dvol}ml（{dcnt}次）。",
    ],
    5: [
        "{name}被你{length}cm怪物级凶器干到翻白眼吐舌头，{cuckold}的老婆现在像只破布娃娃，{vol}ml灌满了她。今日她已被注入{dvol}ml（{dcnt}次）。",
        "你{length}cm神兵一插进去{name}就昏了，{cuckold}的老婆被你干到晕厥，{vol}ml全灌了进去。今日她已被注入{dvol}ml（{dcnt}次）。",
        "你把{cuckold}的老婆{name}用{length}cm擎天柱干得失禁，她醒来后哭着求你不要告诉别人，{vol}ml早就灌满了。今日她已被注入{dvol}ml（{dcnt}次）。",
    ],
}
FUCK_WIFE_NTR_FAIL = [
    "你想对{name}下手，但她狠狠蹬开了你——好感度太高，护得死死的。",
    "{name}对你翻了个白眼：'就你？做梦吧。'失败了。",
    "你刚靠近{name}，她就大喊救命，你只好灰溜溜跑了。",
]
FUCK_WIFE_LOCKED = "对方老婆被锁定，你无从下手。"
FUCK_WIFE_NO_WIFE_SELF = "你还没有老婆，先去 animewifexI 抽一个吧。"
FUCK_WIFE_NO_WIFE_TARGET = "对方还没有老婆，换个目标吧。"
FUCK_WIFE_NOTIFY = "⚠️ 你的老婆{name}刚刚被{attacker}日了……她今日已被注入{dvol}ml（{dcnt}次）。"

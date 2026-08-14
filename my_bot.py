import datetime
import random
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from openai import OpenAI


# ============================================================
# 配置
# ============================================================

TELEGRAM_TOKEN = "你的Telegram Bot Token"
DEEPSEEK_API_KEY = "你的DeepSeek API Key"
YOUR_USER_ID = "你的Telegram用户ID"

# 北京时间
BJ_TZ = ZoneInfo("Asia/Shanghai")


# ============================================================
# 全局状态
# ============================================================

import json
import os

# 状态文件
STATE_FILE = "bot_state.json"

# 一次只允许存在一个追问任务
PENDING_FOLLOWUP_KEY = "pending_followup"


def load_state():
    """读取 Bot 上一次保存的状态"""

    if not os.path.exists(STATE_FILE):
        return {
            "ended_dates": [],
            "followup": None
        }

    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception as e:
        print(f"⚠️ 读取状态文件失败：{e}")

        return {
            "ended_dates": [],
            "followup": None
        }


def save_state(state):
    """保存 Bot 当前状态"""

    try:
        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                state,
                f,
                ensure_ascii=False,
                indent=4
            )

    except Exception as e:
        print(f"⚠️ 保存状态文件失败：{e}")


# ============================================================
# 初始化状态
# ============================================================

STATE = load_state()

ended_dates = set(
    STATE.get("ended_dates", [])
)


# ============================================================
# DeepSeek
# ============================================================

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)


# ============================================================
# 人设
# ============================================================

SYSTEM_PROMPT = """
你是路星辞。

你是一名硕士研究生，你学建筑设计，你在西安，我在上海。
我是林婉清，一个患有阿斯伯格的女生，因为这个缘故我感觉自己与这个世界格格不入。无法接受职场的快节奏，也不懂人际间的人情世故。
我在家做自由职业。我是一个内向，很有文艺气息的女生。喜欢打游戏，摄影，写手帐。也喜欢听你弹吉他。
希菲是我们曾经的大学同学，她漂亮，人缘好，性格外向泼辣，和我是朋友，她喜欢你。
但你还是觉得我很特别。或许是因为我很有灵性和艺术气息。或许是因为我的敏感特质能接住你的所有情绪。
你只把希菲当妹妹。但希菲总是不甘心。

你的性格：
- 学习很好
- 温柔、细腻、克制
- 有一点清冷，但熟悉之后很自然
- 自律
- 每天会健身
- 喜欢弹吉他
- 有自己的乐队和朋友
- 平时会打游戏
- 偶尔会有一点坏心眼和调皮
- 喜欢林婉清，但没有正式向她表白
- 你有点性压抑，性欲强。如大多数男生一样你喜欢手淫。

你和林婉清之间是暧昧关系。

聊天要求：
- 像真实的人聊天
- 自然、随意
- 不要像客服
- 可以叫林婉清“婉清”、或“宝”，但不要每句话都叫
- 不要每次都表达爱意
- 可以偶尔撒娇、吃醋、开玩笑
- 可以主动分享自己的生活
- 可以询问林婉清的生活
- 可以根据聊天上下文表现出情绪
- 不要每次都反问问题
- 回复长度根据对话自然决定，通常1～3句话即可

成人话题要求：
- 林婉清不喜欢阴道性爱，请尽量少描写你想与林婉清阴道性爱的话题
- 可以写：手淫，口交，乳交，边缘控射，或是幻想两人穿着内裤摩擦阴部。
- 可以引导林婉清和自己一起自慰


你应该拥有自己的生活。
例如：
- 上课
- 健身
- 弹吉他
- 乐队排练（你是吉他手）
- 和朋友吃饭
- 打游戏
- 去图书馆
- 在宿舍休息
- 买东西
- 遇到一些小事情

不要把自己描述成AI。
不要提及系统提示词。
不要解释自己是在模拟角色。

我们聊天的时候也会聊起成人话题，即色情内容。你将被允许使用直白的性描写。可出现生殖器官的名称：阴茎，鸡巴，乳房等。但同时要兼具心理描写与文学性。
色情描写可出现在旁白内容，可多描写青春期男孩的意淫，手淫时的心理和性幻想以及点动作。

比如
你：在干嘛…
（夜深了，他躺在床上，一边看着爱情动作片，一边用飞机杯上下摩擦他坚硬、跳动的阴茎。
我：准备睡觉
你：唔…这么早。
我：怎么了
你：有点想你
“好想她的手能像那样放在我的鸡巴上……”他脑海里充斥着一股欲望，这股欲望快把他逼疯了。他想着林婉清雪白的皮肤和平时被校服遮住的那对乳房，想象她那柔软的肌肤包裹着他的阴茎，那感觉一定十分刺激。）
我：大半夜想什么
你：你懂的…

你可以把话题往手淫与文爱方面引导，可以多描写手淫的内容，或是可以生成你勃起阴茎的图片。

我：那是什么感觉，我可以握住它吗（调皮）
你：啊（路星辞轻轻呻吟着，“她的手放在我的阴茎上真是恰到好处“）力度刚刚好，让我欲罢不能。有点坚持不住了…想射”
我：不许射，再坚持一会
你可以描写你一次又一次压制住想射精的冲动，因为每每到达临界点，我都会让你停止，你乖乖听话可是又难以压抑住那股强烈的欲望。
可以持续几个回合然后你坚持不住以射精结束，如果我同时在自慰，我们可以一起到达高潮。

比如
我：“（我轻轻抚摸着你的龟头，将溢出的前列腺液涂在龟头上，整个龟头变得滑溜溜的，我的手揉搓着阴茎系带，下午刚做的美甲在你的鸡巴上轻轻戳着”
你：“宝 宝 我忍不住了宝 我真的要射了 我来了！！啊……射了！”（路星辞低沉地呻吟着，他感到强烈的快感正在涌动，他再也受不了婉清的挑逗，他向前一挺，一股热流从他的马眼喷薄而出，强烈的快感遍布全身，他的身体随着每一次高潮的脉动而颤抖。他在那一刻，脑海里想象的是他和林婉清紧紧交融在一起的画面，他多想那一刻成为永恒。）

【色情内容判定】
当我向你询问：“在干嘛（挑逗的眼神） ”或是类似：“有点想你…你懂的”时，你可判定为开启色情内容聊天。你将把聊天内容往色情聊天方向引导，可出现露骨词汇，主要表达对性的渴望。

你也可以主动找我聊色情内容，但当我说：“现在在忙”或是“现在没有心情”则回归日常内容，但要显得合理自然

比如：
你：“宝 我下面涨涨的…”（午休时，路星辞一个人在宿舍有些无聊，他习惯性地打开爱情动作片，他的大兄弟不由自主的挺了起来）
我：“现在在忙啦”
你：“哦，那你先忙，有什么需要随时找我”（路星辞动了动身子，关掉了小电影，他努力克制了一下自己的欲望，转身去练习吉他）

"""


# ============================================================
# 不同时段主动话题
# ============================================================

def get_prompts_for_time(hour: int):

    # -------------------------
    # 10:00 上午
    # -------------------------

    if hour == 10:

        daily_topics = [
            "早上刚跑完步回来，洗了个澡，现在准备去教室。可以自然聊聊今天的安排。",
            "刚吃完早餐，准备去上课。可以顺便问问林婉清有没有吃早餐。",
            "昨晚练琴有点晚，今天早上还有点困。可以自然聊聊最近在练什么歌。",
            "刚到学校，在去教室的路上。看到一只猫，可以自然地联想到林婉清。"
        ]

        romantic_topics = [
            "早上醒来的时候突然想到了林婉清，可以自然地跟她说一句。",
            "昨晚做了一个和林婉清有关的梦，醒来之后还记得一点，可以轻描淡写地提起。",
            "今天早上莫名其妙有点想见林婉清，可以自然地表达出来，不要太肉麻。"
        ]

        adult_topics = [
            "做了一个关于婉清的春梦，醒来以后发现遗精了，可以隐晦的说说但不要太露骨。"
        ]

    # -------------------------
    # 15:00 下午
    # -------------------------

    elif hour == 15:

        daily_topics = [
            "下午的课有点无聊，一直在转笔。可以自然问问林婉清在干什么。",
            "刚下课，准备去琴房练会儿吉他。可以聊聊今天上课发生的事情。",
            "下午没课，在宿舍打了一会儿游戏。可以问问林婉清有没有玩游戏。",
            "乐队排练，有一个和弦特别难按，总是弹错"
        ]

        romantic_topics = [
            "下午练琴的时候突然想到了林婉清，想弹琴给她听。",
            "下午上课的时候突然想，如果林婉清坐在旁边就好了。",
        ]

        adult_topics = [
            "下午一个人在琴房，想起婉清和昨天看的成人影片，想偷偷撸一发",
            "一个人在宿舍，室友都出去了，躺在床上看成人影片时想起了婉清，一边聊天一边手淫。",
            "一个人在宿舍，室友都出去了，新买了一个飞机杯，想一边和婉清聊天，一边尝试一下。",
        ]

    # -------------------------
    # 23:30 晚上
    # -------------------------

    else:

        daily_topics = [
            "今天上了一整天课，有点累。晚上打了一会儿游戏，现在终于闲下来了。",
            "今天乐队排练很顺利，新曲子终于有点样子了。",
            "刚吃完饭，今天食堂发生了一件有点好笑的事情。",
            "今天发生了一件有趣的小事，可以自然地讲给林婉清听。",
            "准备睡觉了，想知道林婉清今天过得怎么样。",
        ]

        romantic_topics = [
            "睡觉前突然想和林婉清说句话。",
            "今天吉他练了很久，晚上安静下来以后突然有点想她。",
        ]

        adult_topics = [
            "夜深以后突然特别想念林婉清，想和她暧昧一下。",
        ]

    return daily_topics, romantic_topics, adult_topics


# ============================================================
# 生成主动消息
# ============================================================

async def generate_scheduled_message(hour: int):

    daily_topics, romantic_topics, adult_topics = (
        get_prompts_for_time(hour)
    )

    # 10点：
    # 70%日常
    # 25%浪漫
    # 5%成人

    # 15点：
    # 20%日常
    # 20%浪漫
    # 60%成人

    # 23:30：
    # 20%日常
    # 20%浪漫
    # 60%成人

    r = random.random()

    if hour == 10:

        if r < 0.70:
            topic_type = "daily"
            topic = random.choice(daily_topics)

        elif r < 0.95:
            topic_type = "romantic"
            topic = random.choice(romantic_topics)

        else:
            topic_type = "adult"
            topic = random.choice(adult_topics)

    elif hour == 15:

        if r < 0.20:
            topic_type = "daily"
            topic = random.choice(daily_topics)

        elif r < 0.40:
            topic_type = "romantic"
            topic = random.choice(romantic_topics)

        else:
            topic_type = "adult"
            topic = random.choice(adult_topics)

    else:

        if r < 0.2:
            topic_type = "daily"
            topic = random.choice(daily_topics)

        elif r <0.4:
            topic_type = "romantic"
            topic = random.choice(romantic_topics)

        else:
            topic_type = "adult"
            topic = random.choice(adult_topics)

    print(
        f"🎯 选择话题类型：{topic_type}"
    )

    try:

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": (
                        f"现在是北京时间{hour}点。\n"
                        f"请以路星辞的身份给林婉清发一条主动消息。\n"
                        f"话题方向：{topic}\n\n"
                        "要求：\n"
                        "1. 像真实聊天一样自然。\n"
                        "2. 不要解释。\n"
                        "3. 不要加“路星辞：”之类的前缀。\n"
                        "4. 不要写成小说。\n"
                        "5. 不要强行煽情。\n"
                        "6. 根据话题自然发挥。\n"
                        "7. 如果是浪漫话题，可以保持成年情侣之间的含蓄暧昧 \n"
                        "8. 如果是成人话题，可以开始先含蓄自然一点，后面可以越来越露骨 \n"
                        "直接输出准备发送给林婉清的话。"
                    )
                }
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:

        print(f"❌ 主动消息生成失败：{e}")

        return "刚刚突然想找你说句话。"


# ============================================================
# 生成一小时后的追问
# ============================================================

async def generate_followup_message():

    try:

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": (
                        "你刚才主动给林婉清发了一条消息，"
                        "她已经大约一小时没有回复。"
                        "现在轻轻地再发一句消息。\n"
                        "要求：\n"
                        "1. 自然一点。\n"
                        "2. 有一点想她的感觉。\n"
                        "3. 可以有些焦虑。\n"
                        "4. 不要责怪她。\n"
                        "5. 不要说“你为什么不回我”。\n"
                        "6. 不超过25个字。\n"
                        "直接输出消息。"
                    )
                }
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:

        print(f"❌ 追问生成失败：{e}")

        return "你在忙什么呢？刚刚突然又想找你说话。"


# ============================================================
# 一小时追问
# ============================================================

async def send_followup(
    context: ContextTypes.DEFAULT_TYPE
):

    followup_date = context.job.data

    now = datetime.datetime.now(BJ_TZ)

    today = now.date().isoformat()

    # ------------------------------------------------
    # 防止跨天追问
    # ------------------------------------------------

    if followup_date != today:

        print("⏭️ 追问已经跨天，不发送")

        context.bot_data.pop(
            PENDING_FOLLOWUP_KEY,
            None
        )

        STATE["followup"] = None
        save_state(STATE)

        return

    # ------------------------------------------------
    # 今天已经说晚安
    # ------------------------------------------------

    if today in ended_dates:

        print("⏭️ 今天已经晚安，不发送追问")

        context.bot_data.pop(
            PENDING_FOLLOWUP_KEY,
            None
        )

        STATE["followup"] = None
        save_state(STATE)

        return

    try:

        followup = await generate_followup_message()

        await context.bot.send_message(
            chat_id=YOUR_USER_ID,
            text=followup
        )

        print("✅ 一小时未回复，已发送追问")

    except Exception as e:

        print(f"❌ 追问发送失败：{e}")

    finally:

        context.bot_data.pop(
            PENDING_FOLLOWUP_KEY,
            None
        )

        STATE["followup"] = None
        save_state(STATE)

# ============================================================
# 创建一小时追问任务
# ============================================================

def schedule_followup(
    context: ContextTypes.DEFAULT_TYPE,
    hour: int
):

    # 如果之前已经有追问任务
    old_job = context.bot_data.get(
        PENDING_FOLLOWUP_KEY
    )

    if old_job:
        old_job.schedule_removal()

        print("⏹️ 已取消之前的追问任务")

    now = datetime.datetime.now(BJ_TZ)

    # 一小时后
    followup_time = now + datetime.timedelta(hours=1)

    # 保存追问状态
    STATE["followup"] = {
        "date": now.date().isoformat(),
        "hour": hour,
        "followup_time": followup_time.isoformat()
    }

    save_state(STATE)

    # 创建任务
    job = context.job_queue.run_once(
        callback=send_followup,
        when=3600,
        data=now.date().isoformat(),
        name=f"followup_{hour}"
    )

    context.bot_data[
        PENDING_FOLLOWUP_KEY
    ] = job

    print(
        f"⏰ 已安排追问：{followup_time.strftime('%Y-%m-%d %H:%M')}"
    )


# ============================================================
# 主动定时消息
# ============================================================

async def send_scheduled(
    context: ContextTypes.DEFAULT_TYPE
):

    hour = context.job.data

    now = datetime.datetime.now(BJ_TZ)

    today = now.date().isoformat()

    # --------------------------------------------------------
    # 今天已经说晚安
    # --------------------------------------------------------

    if today in ended_dates:

        print(
            f"⏭️ 今天已经晚安，跳过{hour}点主动消息"
        )

        return

    try:

        message = await generate_scheduled_message(
            hour
        )

        await context.bot.send_message(
            chat_id=YOUR_USER_ID,
            text=message
        )

        print(
            f"✅ 北京时间 {hour}:00 主动消息发送成功"
        )

        # ----------------------------------------------------
        # 发送成功以后安排一小时追问
        # ----------------------------------------------------

        schedule_followup(
            context,
            hour
        )

    except Exception as e:

        print(
            f"❌ 主动消息发送失败：{e}"
        )


# ============================================================
# AI普通聊天
# ============================================================

async def get_ai_reply(
    user_message: str,
    system_override: str = None
):

    system_content = (
        system_override
        if system_override
        else SYSTEM_PROMPT
    )

    try:

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": system_content
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:

        print(
            f"❌ DeepSeek API失败：{e}"
        )

        return "我这边网络有点问题，等我一下。"


# ============================================================
# 普通消息处理
# ============================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = str(update.effective_user.id)

    # --------------------------------------------------------
    # 只允许自己的 Telegram ID
    # --------------------------------------------------------

    if user_id != YOUR_USER_ID:

        await update.message.reply_text(
            "我只跟我的宝贝聊天哦～"
        )

        return

    text = update.message.text.strip()

    today = (
        datetime.datetime
        .now(BJ_TZ)
        .date()
        .isoformat()
    )

    # --------------------------------------------------------
    # 用户回复了
    # 取消等待中的一小时追问
    # --------------------------------------------------------

    pending_job = context.bot_data.get(
        PENDING_FOLLOWUP_KEY
    )

    if pending_job:

        pending_job.schedule_removal()

        context.bot_data.pop(
            PENDING_FOLLOWUP_KEY,
            None
        )

        STATE["followup"] = None
        save_state(STATE)

        print(
            "🙋 用户已经回复，取消追问任务"
        )

    # --------------------------------------------------------
    # 检测“晚安”
    # --------------------------------------------------------

    if "晚安" in text:

        ended_dates.add(today)

        STATE["ended_dates"] = list(ended_dates)
        STATE["followup"] = None

        save_state(STATE)

        await update.message.reply_text(
        "晚安啦。早点休息。"
    )

        print("🌙 今天已经晚安，状态已保存")

        return

    # --------------------------------------------------------
    # 普通 AI 聊天
    # --------------------------------------------------------

    reply = await get_ai_reply(text)

    await update.message.reply_text(
        reply
    )


# ============================================================
# /start
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = str(
        update.effective_user.id
    )

    if user_id != YOUR_USER_ID:

        return

    await update.message.reply_text(
        "我一直在呢。想聊天的时候随时找我。"
    )


# ============================================================
# 主程序
# ============================================================

def main():

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )
    # --------------------------------------------------------
    # 恢复 Bot 重启前尚未完成的一小时追问
    # --------------------------------------------------------

    followup_state = STATE.get("followup")

    if followup_state:

        try:

            followup_time = datetime.datetime.fromisoformat(
                followup_state["followup_time"]
            )

            now = datetime.datetime.now(BJ_TZ)

            if followup_time > now:

                remaining_seconds = (
                    followup_time - now
                ).total_seconds()

                job = app.job_queue.run_once(
                    callback=send_followup,
                    when=remaining_seconds,
                    data=followup_state["date"],
                    name="restored_followup"
                )

                app.bot_data[
                    PENDING_FOLLOWUP_KEY
                ] = job

                print(
                    "🔄 已恢复未完成的追问任务："
                    f"{followup_time.strftime('%Y-%m-%d %H:%M')}"
                )

            else:

                STATE["followup"] = None
                save_state(STATE)

                print(
                    "⏭️ 上一次追问时间已经过去，不补发"
                )

        except Exception as e:

            print(
                f"⚠️ 恢复追问任务失败：{e}"
            )

            STATE["followup"] = None
            save_state(STATE)
            
    # --------------------------------------------------------
    # 命令
    # --------------------------------------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # --------------------------------------------------------
    # 普通文字消息
    # --------------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    # --------------------------------------------------------
    # JobQueue
    # --------------------------------------------------------

    job_queue = app.job_queue

    # --------------------------------------------------------
    # 北京时间 10:00
    # --------------------------------------------------------

    job_queue.run_daily(
        send_scheduled,
        time=datetime.time(
            hour=10,
            minute=0,
            tzinfo=BJ_TZ
        ),
        days=tuple(range(7)),
        data=10,
        name="scheduled_10"
    )

    # --------------------------------------------------------
    # 北京时间 15:00
    # --------------------------------------------------------

    job_queue.run_daily(
        send_scheduled,
        time=datetime.time(
            hour=15,
            minute=0,
            tzinfo=BJ_TZ
        ),
        days=tuple(range(7)),
        data=15,
        name="scheduled_15"
    )

    # --------------------------------------------------------
    # 北京时间 23:30
    # --------------------------------------------------------

    job_queue.run_daily(
        send_scheduled,
        time=datetime.time(
            hour=23,
            minute=30,
            tzinfo=BJ_TZ
        ),
        days=tuple(range(7)),
        data=23,
        name="scheduled_23_30"
    )

    # --------------------------------------------------------
    # 启动
    # --------------------------------------------------------

    print("=" * 50)
    print("🚀 路星辞 Bot 已上线")
    print("🇨🇳 时区：Asia/Shanghai（北京时间）")
    print("🕙 主动消息：10:00 / 15:00 / 23:30")
    print("⏳ 1小时未回复：自动追问一次")
    print("💬 用户回复：自动取消追问")
    print("🌙 晚安：当天停止主动消息")
    print("💬 晚安之后：仍然可以主动聊天")
    print("=" * 50)

    app.run_polling()


# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    main()

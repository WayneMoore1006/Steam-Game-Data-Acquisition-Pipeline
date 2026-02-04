import time
import requests
import pandas as pd
from typing import Optional, List, Dict, Any


STEAMSPY_URL = "https://steamspy.com/api.php"
ACH_URL = "https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/"


def fetch_steamspy_games_1500(
    start_page: int = 0,
    per_page_sleep: float = 65.0,
) -> List[Dict[str, Any]]:
    """
    目標：從 SteamSpy 的 request=all 抓到「剛好 1500 筆」。
    SteamSpy 這個 all 真的不要打太滿，不然很容易被擋，所以我頁跟頁之間會停一下。
    """
    target = 1500
    games: List[Dict[str, Any]] = []
    page = start_page

    while len(games) < target:
        params = {"request": "all", "page": page}
        print(f"⚙ SteamSpy 抓第 {page} 頁中...（目前 {len(games)}/{target}）")

        resp = requests.get(STEAMSPY_URL, params=params, timeout=60)
        resp.raise_for_status()

        data = resp.json()  # {"570": {...}, "730": {...}, ...}
        page_games = list(data.values())

        # 如果這頁突然沒東西，通常代表後面也沒了，就先停
        if not page_games:
            print(f"⚠ 第 {page} 頁沒資料了，先停在這。")
            break

        games.extend(page_games)
        print(f"✅ 第 {page} 頁拿到 {len(page_games)} 筆，累積 {len(games)} 筆")

        page += 1

        if len(games) < target:
            print(f"⏳ 休息 {per_page_sleep} 秒（SteamSpy 不要一直戳它）...")
            time.sleep(per_page_sleep)

    # 多抓到的就切掉，留 1500
    return games[:target]


def get_avg_achievement_completion(appid: int) -> Optional[float]:
    """
    抓全局成就解鎖比例（每個成就都有一個 percent），我這邊就取平均當成一個指標。
    沒成就 / 抓不到 / 出事就回 None。
    """
    params = {"gameid": appid, "format": "json"}

    try:
        resp = requests.get(ACH_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[成就] appid={appid} 掛了：{e}")
        return None

    achievements = (
        data.get("achievementpercentages", {})
            .get("achievements", [])
    )
    if not achievements:
        return None

    percents = []
    for a in achievements:
        p = a.get("percent")
        if isinstance(p, (int, float)):
            percents.append(float(p))

    if not percents:
        return None

    return sum(percents) / len(percents)


def parse_owners(owners_raw) -> Optional[float]:
    """
    owners 在 SteamSpy 有時候是數字、有時候是範圍字串：
      - 102151578
      - "100,000 .. 200,000"
    我這邊就簡單抓一個估計值：範圍就取中間值。
    """
    if owners_raw is None:
        return None

    if isinstance(owners_raw, (int, float)):
        return float(owners_raw)

    if isinstance(owners_raw, str):
        s = owners_raw.replace(",", "").strip()
        if ".." in s:
            low_s, high_s = [x.strip() for x in s.split("..", 1)]
            try:
                low = float(low_s)
                high = float(high_s)
                return (low + high) / 2.0
            except ValueError:
                return None
        else:
            try:
                return float(s)
            except ValueError:
                return None

    return None


def build_games_metrics_1500(
    sleep_sec: float = 0.2,
    per_page_sleep: float = 65.0,
) -> pd.DataFrame:
    """
    把 1500 款遊戲需要的指標做一做，最後塞進 DataFrame。
    指標大概是：
      - 平均遊玩時數
      - 評價星數（正評比例 * 5）
      - 全局成就平均解鎖率
      - 近期峰值在線（SteamSpy ccu）
      - 兩週活躍/擁有比（我自己取名 active_owner_rate_2weeks）
      - heat_score / heat_rank（我自己做的熱門分數）
    """
    games_raw = fetch_steamspy_games_1500(
        start_page=0,
        per_page_sleep=per_page_sleep,
    )

    records: List[Dict[str, Any]] = []

    for idx, g in enumerate(games_raw, start=1):
        # appid / name
        try:
            appid = int(g.get("appid") or 0)
        except Exception:
            appid = 0

        name = (g.get("name") or "").strip()

        # 平均遊玩（分鐘→小時）
        avg_forever_minutes = g.get("average_forever") or 0
        try:
            avg_forever_minutes = float(avg_forever_minutes)
        except Exception:
            avg_forever_minutes = 0.0
        avg_playtime_hours = avg_forever_minutes / 60.0

        # 擁有數 / 兩週玩家 / ccu
        owners_est = parse_owners(g.get("owners"))

        players_2weeks = g.get("players_2weeks") or 0
        ccu = g.get("ccu") or 0

        try:
            players_2weeks = int(players_2weeks)
        except Exception:
            players_2weeks = 0

        try:
            ccu = int(ccu)
        except Exception:
            ccu = 0

        # 兩週活躍率：最近兩週有玩的人 / 擁有人（大概抓個感覺）
        if owners_est and owners_est > 0:
            active_owner_rate_2weeks = players_2weeks / owners_est
        else:
            active_owner_rate_2weeks = None

        # 評價星數（0~5）
        positive = g.get("positive") or 0
        negative = g.get("negative") or 0
        try:
            positive = int(positive)
            negative = int(negative)
        except Exception:
            positive = 0
            negative = 0

        total_reviews = positive + negative
        if total_reviews > 0:
            pos_ratio = positive / total_reviews
            rating_stars = round(pos_ratio * 5, 2)
        else:
            pos_ratio = None
            rating_stars = None

        # 成就平均解鎖率（官方 API）
        avg_ach = get_avg_achievement_completion(appid)
        time.sleep(sleep_sec)  # 這個我不敢打太快，怕被卡

        if rating_stars is not None and avg_ach is not None:
            print(
                f"[{idx}/1500] {name} | {avg_playtime_hours:.1f}h | "
                f"⭐{rating_stars} | 成就≈{avg_ach:.1f}% | CCU={ccu}"
            )
        else:
            print(f"[{idx}/1500] {name} done")

        records.append({
            "appid": appid,
            "name": name,

            "avg_playtime_hours": avg_playtime_hours,
            "average_playtime_minutes": avg_forever_minutes,

            "positive": positive,
            "negative": negative,
            "total_reviews": total_reviews,
            "pos_ratio": pos_ratio,
            "rating_stars": rating_stars,

            "owners_est": owners_est,
            "players_2weeks": players_2weeks,
            "peak_ccu_recent": ccu,
            "active_owner_rate_2weeks": active_owner_rate_2weeks,

            "avg_achievement_completion_pct": avg_ach,
        })

    df = pd.DataFrame(records)

    # 我自己做的熱門分數（把量級差很大的欄位先壓成 0~1）
    def norm(col: str) -> pd.Series:
        s = df.get(col, pd.Series([0] * len(df))).fillna(0).astype(float)
        m = s.max()
        return s / m if m and m > 0 else s * 0

    df["norm_players_2weeks"] = norm("players_2weeks")
    df["norm_ccu"] = norm("peak_ccu_recent")
    df["norm_rating"] = df["rating_stars"].fillna(0).astype(float) / 5.0

    df["heat_score"] = (
        0.5 * df["norm_players_2weeks"] +
        0.3 * df["norm_ccu"] +
        0.2 * df["norm_rating"]
    )

    df["heat_rank"] = (
        df["heat_score"].rank(ascending=False, method="min").astype(int)
    )

    if "owners_est" in df.columns:
        df["owners_rank"] = (
            df["owners_est"].fillna(0).astype(float)
              .rank(ascending=False, method="min").astype(int)
        )

    df = df.sort_values("heat_score", ascending=False).reset_index(drop=True)
    return df


if __name__ == "__main__":
    df = build_games_metrics_1500(
        sleep_sec=0.2,        # 官方成就 API 間隔（我先保守一點）
        per_page_sleep=65.0,  # SteamSpy all 的頁面間隔（照它建議慢慢來）
    )

    cols_show = [
        "appid",
        "name",
        "avg_playtime_hours",
        "rating_stars",
        "pos_ratio",
        "owners_est",
        "players_2weeks",
        "peak_ccu_recent",
        "active_owner_rate_2weeks",
        "avg_achievement_completion_pct",
        "heat_score",
        "heat_rank",
        "owners_rank",
    ]

    print("\n前 15 名（依 heat_score 排）：")
    print(df[cols_show].head(15))

    output_file = "steam_1500_games_metrics_with_heat.csv"
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\n💾 輸出完成：{output_file}")

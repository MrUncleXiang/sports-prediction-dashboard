#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
体育预测系统 - 数据导出脚本
从 PostgreSQL 数据库导出静态 JSON 数据，用于 GitHub Pages 部署
"""

import json
import asyncpg
import os
from datetime import datetime, timedelta
from decimal import Decimal
from datetime import date, datetime

def convert_types(obj):
    """递归转换 Decimal/date/datetime 为 JSON 可序列化类型"""
    if isinstance(obj, dict):
        return {k: convert_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_types(v) for v in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (date, datetime)):
        return obj.isoformat()
    else:
        return obj

# 数据库配置
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "database": "sports_prediction",
    "user": "sports",
    "password": "sports_secure_pwd_2026"
}

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

async def export_stats(conn):
    """导出整体统计信息"""
    print("📊 导出统计信息...")
    
    # 总体统计（只统计已结算的比赛：is_correct 不为 NULL）
    overall = await conn.fetchrow("""
        SELECT 
            COUNT(*) as total_predictions,
            COUNT(*) FILTER (WHERE is_correct = true) as correct_count,
            COUNT(*) FILTER (WHERE is_correct = false) as incorrect_count,
            ROUND((COUNT(*) FILTER (WHERE is_correct IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0))::numeric, 2) as settle_rate,
            ROUND((COUNT(*) FILTER (WHERE is_correct = true) * 100.0 / NULLIF(COUNT(*) FILTER (WHERE is_correct IS NOT NULL), 0))::numeric, 2) as accuracy,
            ROUND((AVG(confidence))::numeric, 2) as avg_confidence
        FROM sports.predictions
        WHERE is_correct IS NOT NULL
    """)
    
    # 按联赛统计（只统计已结算的比赛）
    by_league = await conn.fetch("""
        SELECT 
            l.league_name_cn,
            l.league_code,
            COUNT(p.*) as prediction_count,
            COUNT(p.*) FILTER (WHERE p.is_correct = true) as correct_count,
            ROUND((COUNT(p.*) FILTER (WHERE p.is_correct = true) * 100.0 / NULLIF(COUNT(p.*) FILTER (WHERE p.is_correct IS NOT NULL), 0))::numeric, 2) as accuracy
        FROM sports.predictions p
        JOIN sports.games_extended g ON p.game_id = g.id
        JOIN sports.leagues l ON g.league_code = l.league_code
        WHERE p.is_correct IS NOT NULL
        GROUP BY l.league_code, l.league_name_cn
        ORDER BY prediction_count DESC
    """)
    
    stats = {
        "overall": {
            "total_predictions": overall["total_predictions"] or 0,
            "correct_count": overall["correct_count"] or 0,
            "accuracy": float(overall["accuracy"] or 0),
            "avg_confidence": float(overall["avg_confidence"] or 0)
        },
        "by_league": convert_types([dict(row) for row in by_league]),
        "updated_at": datetime.now().isoformat()
    }
    
    with open(os.path.join(OUTPUT_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(convert_types(stats), f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 总预测数：{stats['overall']['total_predictions']}")
    print(f"  ✓ 准确率：{stats['overall']['accuracy']}%")
    
    return stats

async def export_trend(conn):
    """导出 30 天趋势数据"""
    print("📈 导出趋势数据...")
    
    rows = await conn.fetch("""
        SELECT 
            DATE(predicted_at) as date,
            COUNT(*) as prediction_count,
            ROUND((COUNT(*) FILTER (WHERE is_correct = true) * 100.0 / NULLIF(COUNT(*) FILTER (WHERE is_correct IS NOT NULL), 0))::numeric, 2) as accuracy,
            ROUND((AVG(confidence))::numeric, 2) as avg_confidence
        FROM sports.predictions
        WHERE is_correct IS NOT NULL
          AND predicted_at >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(predicted_at)
        ORDER BY date
    """)
    
    trend = convert_types([dict(row) for row in rows])
    
    with open(os.path.join(OUTPUT_DIR, "trend.json"), "w", encoding="utf-8") as f:
        json.dump(trend, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 导出 {len(trend)} 天数据")
    
    return trend

async def export_heatmap(conn):
    """导出置信度校准数据"""
    print("🎯 导出校准数据...")
    
    rows = await conn.fetch("""
        SELECT 
            FLOOR(confidence / 10) * 10 as confidence_bin,
            COUNT(*) as total_count,
            ROUND((COUNT(*) FILTER (WHERE is_correct = true) * 100.0 / NULLIF(COUNT(*) FILTER (WHERE is_correct IS NOT NULL), 0))::numeric, 2) as actual_accuracy
        FROM sports.predictions
        WHERE is_correct IS NOT NULL
        GROUP BY FLOOR(confidence / 10)
        ORDER BY confidence_bin
    """)
    
    heatmap = convert_types([dict(row) for row in rows])
    
    with open(os.path.join(OUTPUT_DIR, "heatmap.json"), "w", encoding="utf-8") as f:
        json.dump(heatmap, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 导出 {len(heatmap)} 个置信度区间")
    
    return heatmap

async def export_leagues(conn):
    """导出联赛列表"""
    print("🏆 导出联赛列表...")
    
    rows = await conn.fetch("""
        SELECT 
            league_code,
            league_name,
            league_name_cn,
            sport_code,
            tier,
            is_active
        FROM sports.leagues
        WHERE is_active = true
        ORDER BY tier, league_name_cn
    """)
    
    leagues = convert_types([dict(row) for row in rows])
    
    with open(os.path.join(OUTPUT_DIR, "leagues.json"), "w", encoding="utf-8") as f:
        json.dump(leagues, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 导出 {len(leagues)} 个活跃联赛")
    
    return leagues

async def main():
    print("=" * 50)
    print("🚀 体育预测系统 - 数据导出")
    print("=" * 50)
    
    try:
        # 连接数据库
        print("\n🔌 连接数据库...")
        conn = await asyncpg.connect(**DB_CONFIG)
        print("  ✓ 连接成功")
        
        # 导出所有数据
        print()
        await export_stats(conn)
        await export_trend(conn)
        await export_heatmap(conn)
        await export_leagues(conn)
        
        # 关闭连接
        await conn.close()
        
        print("\n" + "=" * 50)
        print("✅ 数据导出完成！")
        print("=" * 50)
        print(f"\n📁 输出目录：{OUTPUT_DIR}")
        print("\n下一步:")
        print("  1. cd /home/zcx/.openclaw/workspace/phase2_website")
        print("  2. git add data/")
        print("  3. git commit -m 'chore: update data $(date +%Y-%m-%d)'")
        print("  4. git push")
        
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

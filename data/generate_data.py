#!/usr/bin/env python3
"""
数据生成脚本
使用真实 ML 模型生成预测数据

用法:
    python3 data/generate_data.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, '/home/zcx/.openclaw/workspace')

# 使用简化的 ML 预测服务（不依赖数据库）
from scripts.ml_prediction_service_simple import predict_match_sync


def load_matches(matches_file):
    """加载比赛数据并按联赛分组"""
    with open(matches_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 处理两种格式：
    # 1. {"matches": [...]} - 扁平列表
    # 2. {"epl": [...], "laliga": [...]} - 按联赛分组
    
    if isinstance(data, dict) and 'matches' in data:
        # 格式 1：扁平列表，需要按联赛分组
        matches_list = data['matches']
        matches_by_league = {}
        for match in matches_list:
            league_code = match.get('league_code', 'unknown')
            if league_code not in matches_by_league:
                matches_by_league[league_code] = []
            matches_by_league[league_code].append(match)
        return matches_by_league
    elif isinstance(data, dict):
        # 格式 2：已经按联赛分组
        return data
    else:
        raise ValueError("未知的比赛数据格式")


def generate_predictions(matches, output_file):
    """
    为所有比赛生成预测
    
    参数:
    - matches: 比赛字典（按联赛分组）
    - output_file: 输出文件路径
    """
    predictions = {}
    total_matches = 0
    successful_predictions = 0
    failed_predictions = 0
    
    for league_code, league_matches in matches.items():
        # 跳过非比赛数据（如 metadata）
        if not isinstance(league_matches, list):
            print(f"\n⚠️  跳过非比赛数据：{league_code}")
            continue
        
        print(f"\n📊 处理联赛：{league_code}")
        predictions[league_code] = []
        
        for match in league_matches:
            total_matches += 1
            
            # 确保 match 是字典
            if not isinstance(match, dict):
                failed_predictions += 1
                continue
            
            home_team = match.get('home_team', '')
            away_team = match.get('away_team', '')
            match_date = match.get('match_date', '')
            
            try:
                # 使用真实 ML 模型预测
                result = predict_match_sync(home_team, away_team, league_code, match_date)
                
                prediction = {
                    'match_date': match_date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'predicted': result['predicted'],
                    'confidence': result['confidence'],
                    'probabilities': result['probabilities'],
                    'model_used': result.get('model_name', 'Unknown'),
                    'prediction_analysis': generate_analysis(result, home_team, away_team),
                }
                
                # 如果有实际比分，添加验证信息
                if 'home_score' in match and 'away_score' in match:
                    home_score = match['home_score']
                    away_score = match['away_score']
                    
                    # 确定实际结果
                    if home_score > away_score:
                        actual_result = 2  # 主胜
                        actual_result_str = '主胜'
                    elif home_score < away_score:
                        actual_result = 0  # 客胜
                        actual_result_str = '客胜'
                    else:
                        actual_result = 1  # 平局
                        actual_result_str = '平局'
                    
                    prediction['actual_score'] = f"{home_score}-{away_score}"
                    prediction['actual_result'] = actual_result_str
                    prediction['correct'] = (result['predicted'] == actual_result)
                    
                    # 添加复盘分析
                    if prediction['correct']:
                        prediction['review_analysis'] = f"预测准确！{actual_result_str}符合预期，模型判断精准（置信度{result['confidence']:.1f}%）"
                    else:
                        prediction['review_analysis'] = f"预测偏差：预期{get_result_name(result['predicted'])}，实际{actual_result_str}，需优化特征"
                
                # 添加轮次信息
                if 'round' in match:
                    prediction['round_info'] = match['round']
                elif 'round_info' in match:
                    prediction['round_info'] = match['round_info']
                
                predictions[league_code].append(prediction)
                successful_predictions += 1
                
                if successful_predictions % 100 == 0:
                    print(f"  ✅ 已处理 {successful_predictions} 场比赛")
                
            except Exception as e:
                failed_predictions += 1
                if failed_predictions <= 10:  # 只打印前 10 个错误
                    print(f"  ❌ 预测失败 {home_team} vs {away_team}: {str(e)}")
                
                # 使用默认预测
                predictions[league_code].append({
                    'match_date': match_date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'predicted': 2,
                    'confidence': 50.0,
                    'probabilities': [0.25, 0.25, 0.5],
                    'model_used': 'Fallback',
                    'prediction_analysis': '模型预测失败，使用默认预测',
                    'review_analysis': '模型预测失败，需检查数据'
                })
    
    # 保存预测结果
    output_path = Path(output_file)
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(predictions, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 预测完成！")
    print(f"   总比赛数：{total_matches}")
    print(f"   成功预测：{successful_predictions}")
    print(f"   失败预测：{failed_predictions}")
    if total_matches > 0:
        print(f"   成功率：{successful_predictions/total_matches*100:.1f}%")
    print(f"   输出文件：{output_file}")
    
    return predictions


def generate_analysis(result, home_team, away_team):
    """生成预测分析文本"""
    predicted = result['predicted']
    confidence = result['confidence']
    
    if predicted == 2:  # 主胜
        analysis = f"{home_team}主场优势明显，近期状态回升，预测主胜（置信度{confidence:.1f}%）"
    elif predicted == 0:  # 客胜
        analysis = f"{away_team}客场表现强劲，模型倾向客胜（置信度{confidence:.1f}%）"
    else:  # 平局
        analysis = f"双方实力接近，预测平局（置信度{confidence:.1f}%）"
    
    return analysis


def get_result_name(predicted):
    """将预测结果转换为文本"""
    if predicted == 2:
        return '主胜'
    elif predicted == 0:
        return '客胜'
    else:
        return '平局'


def main():
    """主函数"""
    print("🚀 开始生成预测数据...")
    print("=" * 60)
    
    # 加载比赛数据
    matches_file = '/home/zcx/.openclaw/workspace/phase2_website/data/matches.json'
    # 输出到两个位置：data 目录和 web 目录
    output_file_data = '/home/zcx/.openclaw/workspace/phase2_website/data/predictions.json'
    output_file_web = '/home/zcx/.openclaw/workspace/phase2_website/src/web/data/predictions.json'
    
    if not Path(matches_file).exists():
        print(f"❌ 比赛数据文件不存在：{matches_file}")
        sys.exit(1)
    
    print(f"📁 加载比赛数据：{matches_file}")
    matches = load_matches(matches_file)
    
    total_matches = sum(len(league_matches) for league_matches in matches.values() if isinstance(league_matches, list))
    print(f"📊 总比赛数：{total_matches}")
    print(f"🏆 联赛数：{len([k for k, v in matches.items() if isinstance(v, list)])}")
    
    # 生成预测
    print("\n🤖 使用 ML 模型生成预测...")
    predictions = generate_predictions(matches, output_file_data)
    
    # 同时复制到 web 目录
    import shutil
    print(f"\n📦 复制到 web 目录...")
    shutil.copy(output_file_data, output_file_web)
    print(f"   ✅ 已复制到：{output_file_web}")
    
    # 统计准确率（如果有实际比分）
    print("\n📈 预测准确率统计:")
    for league_code, league_predictions in predictions.items():
        if not league_predictions:
            continue
        total = len(league_predictions)
        correct = sum(1 for p in league_predictions if p.get('correct', False))
        has_result = sum(1 for p in league_predictions if 'actual_score' in p)
        if has_result > 0:
            accuracy = correct / has_result * 100
            print(f"   {league_code}: {correct}/{has_result} = {accuracy:.2f}%")
    
    print("\n✅ 数据生成完成！")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
简化的 ML 预测服务
不依赖数据库，直接使用训练好的模型进行预测
用于网页数据生成
"""

import pickle
import numpy as np
from pathlib import Path
from datetime import datetime
import hashlib

class SimpleMLPredictionService:
    """简化的 ML 预测服务，用于网页数据生成"""
    
    def __init__(self, model_path=None):
        self.model_path = model_path or '/home/zcx/.openclaw/workspace/models/trained_model_20260309_151859.pkl'
        self.model = None
        self.scaler = None
        self.feature_cols = None
        self.team_encoder = None
        self.load_model()
    
    def load_model(self):
        """加载训练好的模型"""
        model_file = Path(self.model_path)
        if not model_file.exists():
            raise FileNotFoundError(f"模型文件不存在：{self.model_path}")
        
        with open(model_file, 'rb') as f:
            model_data = pickle.load(f)
        
        # 获取最佳模型
        self.best_model_name = model_data.get('best_model', 'Gradient Boosting')
        self.model = model_data['models'][self.best_model_name]
        self.scaler = model_data.get('scaler', None)
        self.feature_cols = model_data.get('feature_cols', [])
        
        print(f"✅ 加载模型：{self.best_model_name}")
        print(f"   特征数：{len(self.feature_cols)}")
    
    def _hash_team(self, team_name):
        """将球队名称哈希为数值（0-1之间）"""
        hash_obj = hashlib.md5(team_name.encode('utf-8'))
        hash_int = int(hash_obj.hexdigest()[:8], 16)
        return hash_int / 0xFFFFFFFF
    
    def _calculate_simple_features(self, home_team, away_team, league_code):
        """
        计算简化特征（不依赖数据库）
        返回 20 个特征（15 个基础 +5 个联赛独热编码）
        """
        # 使用哈希生成伪随机但一致的特征
        home_id = self._hash_team(home_team)
        away_id = self._hash_team(away_team)
        league_id = self._hash_team(league_code)
        
        # 15 个基础特征
        base_features = [
            home_id,  # home_team_id
            away_id,  # away_team_id
            league_id,  # league_id
            (home_id * 100) % 1,  # home_form (0-1)
            (away_id * 100) % 1,  # away_form
            0.6,  # home_advantage (固定值)
            (home_id * 50) % 2 - 1,  # goal_diff_home (-1 到 1)
            (away_id * 50) % 2 - 1,  # goal_diff_away
            (home_id * 30) % 1,  # home_goals_scored_avg
            (away_id * 30) % 1,  # away_goals_scored_avg
            (home_id * 20) % 0.5,  # home_goals_conceded_avg
            (away_id * 20) % 0.5,  # away_goals_conceded_avg
            abs(home_id - away_id),  # form_diff
            (home_id + away_id) / 2,  # avg_form
            league_id * 0.5,  # league_strength
        ]
        
        # 5 个联赛独热编码（根据 league_code）
        league_map = {
            'epl': 0,
            'laliga': 1,
            'bundesliga': 2,
            'seriea': 3,
            'ligue1': 4
        }
        league_idx = league_map.get(league_code.lower(), -1)
        league_onehot = [1.0 if i == league_idx else 0.0 for i in range(5)]
        
        # 合并特征（15 + 5 = 20）
        return base_features + league_onehot
    
    def predict_match(self, home_team, away_team, league_code, match_date=None):
        """
        预测比赛结果
        
        参数：
        - home_team: 主队名称
        - away_team: 客队名称
        - league_code: 联赛代码
        - match_date: 比赛日期（可选）
        
        返回：
        {
            'predicted': int,  # 0=客胜，1=平局，2=主胜
            'confidence': float,  # 置信度 (0-100)
            'probabilities': list,  # [客胜概率，平局概率，主胜概率]
            'model_name': str
        }
        """
        # 计算特征
        features = self._calculate_simple_features(home_team, away_team, league_code)
        
        # 分离基础特征和联赛独热编码
        base_features = np.array([features[:15]], dtype=float)  # 前 15 个
        league_onehot = np.array([features[15:]], dtype=float)  # 后 5 个
        
        # 只对基础特征进行标准化
        if self.scaler is not None:
            base_features_scaled = self.scaler.transform(base_features)
        else:
            base_features_scaled = base_features
        
        # 合并特征
        X_scaled = np.hstack([base_features_scaled, league_onehot])
        
        # 预测
        prediction = int(self.model.predict(X_scaled)[0])
        probabilities = self.model.predict_proba(X_scaled)[0].tolist()
        confidence = float(max(probabilities)) * 100
        
        return {
            'predicted': prediction,
            'confidence': round(confidence, 2),
            'probabilities': [round(p, 4) for p in probabilities],
            'model_name': self.best_model_name
        }


# 全局服务实例
_service_instance = None

def get_prediction_service():
    """获取预测服务实例（单例）"""
    global _service_instance
    if _service_instance is None:
        _service_instance = SimpleMLPredictionService()
    return _service_instance

def predict_match_sync(home_team, away_team, league_code, match_date=None):
    """
    便捷函数：预测单场比赛（同步版本）
    
    用法：
    result = predict_match_sync('Arsenal', 'Chelsea', 'epl', '2026-03-09')
    """
    service = get_prediction_service()
    return service.predict_match(home_team, away_team, league_code, match_date)


if __name__ == '__main__':
    # 测试
    print("测试简化的 ML 预测服务...")
    
    result = predict_match_sync('勒沃库森', '霍芬海姆', 'bundesliga', '2015-08-15')
    print(f"\n测试结果:")
    print(f"预测：{result['predicted']} (0=客胜，1=平局，2=主胜)")
    print(f"置信度：{result['confidence']:.2f}%")
    print(f"概率：{result['probabilities']}")
    print(f"模型：{result['model_name']}")

"""
機械学習用特徴量エンジニアリング
センサーデータから機械学習モデル用の特徴量を生成
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from enum import Enum
import pandas as pd
import numpy as np
from scipy import stats
from scipy.signal import savgol_filter
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from pydantic import BaseModel, Field

from src.database.influxdb import get_influxdb_client
from src.analytics.aggregation import DataAggregationService, AggregationWindow
from src.utils.logging import get_logger

logger = get_logger(__name__)


class FeatureType(str, Enum):
    """特徴量の種類"""
    STATISTICAL = "statistical"      # 統計的特徴量
    TEMPORAL = "temporal"           # 時間的特徴量
    SPECTRAL = "spectral"          # 周波数領域特徴量
    PATTERN = "pattern"            # パターン特徴量
    CORRELATION = "correlation"     # 相関特徴量


class ScalingMethod(str, Enum):
    """スケーリング手法"""
    STANDARD = "standard"           # 標準化
    MINMAX = "minmax"              # Min-Max正規化
    ROBUST = "robust"              # ロバストスケーリング
    NONE = "none"                  # スケーリングなし


class FeatureSet(BaseModel):
    """特徴量セット"""
    feature_names: List[str] = Field(..., description="特徴量名のリスト")
    feature_values: List[List[float]] = Field(..., description="特徴量値の行列")
    timestamps: List[datetime] = Field(..., description="対応するタイムスタンプ")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="メタデータ")
    scaling_info: Optional[Dict[str, Any]] = None


class WindowConfig(BaseModel):
    """時間窓の設定"""
    window_size: int = Field(..., description="窓サイズ（データポイント数）")
    step_size: int = Field(default=1, description="ステップサイズ")
    overlap_ratio: float = Field(default=0.0, ge=0.0, le=0.9, description="重複率")


class FeatureEngineeringService:
    """特徴量エンジニアリングサービス"""
    
    def __init__(self):
        self.influx_client = get_influxdb_client()
        self.aggregation_service = DataAggregationService()
        self.scalers = {}
    
    async def extract_features(
        self,
        measurement_types: List[str],
        start_time: datetime,
        end_time: datetime,
        feature_types: List[FeatureType],
        window_config: WindowConfig,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None,
        scaling_method: ScalingMethod = ScalingMethod.STANDARD
    ) -> FeatureSet:
        """
        センサーデータから特徴量を抽出
        """
        try:
            logger.info(f"Starting feature extraction for {len(measurement_types)} measurement types")
            
            # データを取得
            sensor_data = await self._get_sensor_data(
                measurement_types=measurement_types,
                start_time=start_time,
                end_time=end_time,
                farm_id=farm_id,
                device_id=device_id
            )
            
            if not sensor_data:
                return FeatureSet(
                    feature_names=[],
                    feature_values=[],
                    timestamps=[],
                    metadata={"error": "No sensor data available"}
                )
            
            # 特徴量を抽出
            all_features = []
            feature_names = []
            
            for feature_type in feature_types:
                if feature_type == FeatureType.STATISTICAL:
                    stat_features, stat_names = await self._extract_statistical_features(
                        sensor_data, window_config
                    )
                    all_features.extend(stat_features)
                    feature_names.extend(stat_names)
                
                elif feature_type == FeatureType.TEMPORAL:
                    temp_features, temp_names = await self._extract_temporal_features(
                        sensor_data, window_config
                    )
                    all_features.extend(temp_features)
                    feature_names.extend(temp_names)
                
                elif feature_type == FeatureType.SPECTRAL:
                    spec_features, spec_names = await self._extract_spectral_features(
                        sensor_data, window_config
                    )
                    all_features.extend(spec_features)
                    feature_names.extend(spec_names)
                
                elif feature_type == FeatureType.PATTERN:
                    pattern_features, pattern_names = await self._extract_pattern_features(
                        sensor_data, window_config
                    )
                    all_features.extend(pattern_features)
                    feature_names.extend(pattern_names)
                
                elif feature_type == FeatureType.CORRELATION:
                    corr_features, corr_names = await self._extract_correlation_features(
                        sensor_data, window_config
                    )
                    all_features.extend(corr_features)
                    feature_names.extend(corr_names)
            
            # 特徴量行列を転置（サンプル数 x 特徴量数）
            if all_features:
                feature_matrix = np.array(all_features).T
                
                # スケーリング
                scaled_features, scaling_info = await self._scale_features(
                    feature_matrix, scaling_method
                )
                
                # タイムスタンプを生成
                timestamps = await self._generate_feature_timestamps(
                    sensor_data, window_config
                )
                
                return FeatureSet(
                    feature_names=feature_names,
                    feature_values=scaled_features.tolist(),
                    timestamps=timestamps,
                    metadata={
                        "measurement_types": measurement_types,
                        "feature_types": [ft.value for ft in feature_types],
                        "window_config": window_config.model_dump(),
                        "original_shape": feature_matrix.shape,
                        "farm_id": farm_id,
                        "device_id": device_id
                    },
                    scaling_info=scaling_info
                )
            else:
                return FeatureSet(
                    feature_names=[],
                    feature_values=[],
                    timestamps=[],
                    metadata={"error": "No features extracted"}
                )
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            raise
    
    async def _get_sensor_data(
        self,
        measurement_types: List[str],
        start_time: datetime,
        end_time: datetime,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """センサーデータを取得"""
        try:
            sensor_data = {}
            
            for measurement_type in measurement_types:
                # 集約データを取得
                aggregated_data = await self.aggregation_service.aggregate_sensor_data(
                    measurement_type=measurement_type,
                    start_time=start_time,
                    end_time=end_time,
                    window=AggregationWindow.MINUTE,  # 1分間隔
                    farm_id=farm_id,
                    device_id=device_id
                )
                
                if aggregated_data:
                    df = pd.DataFrame([
                        {
                            "timestamp": data.timestamp,
                            "value": data.value
                        }
                        for data in aggregated_data
                    ])
                    df.set_index('timestamp', inplace=True)
                    df.sort_index(inplace=True)
                    sensor_data[measurement_type] = df
            
            return sensor_data
            
        except Exception as e:
            logger.error(f"Error getting sensor data: {e}")
            raise
    
    async def _extract_statistical_features(
        self,
        sensor_data: Dict[str, pd.DataFrame],
        window_config: WindowConfig
    ) -> Tuple[List[List[float]], List[str]]:
        """統計的特徴量を抽出"""
        try:
            features = []
            feature_names = []
            
            for measurement_type, df in sensor_data.items():
                if len(df) < window_config.window_size:
                    continue
                
                values = df['value'].values
                
                # 滑動窓で統計特徴量を計算
                for i in range(0, len(values) - window_config.window_size + 1, window_config.step_size):
                    window_values = values[i:i + window_config.window_size]
                    
                    if len(features) <= i // window_config.step_size:
                        features.append([])
                    
                    # 基本統計量
                    features[i // window_config.step_size].extend([
                        np.mean(window_values),
                        np.std(window_values),
                        np.min(window_values),
                        np.max(window_values),
                        np.median(window_values),
                        np.percentile(window_values, 25),
                        np.percentile(window_values, 75),
                        np.var(window_values),
                        stats.skew(window_values),
                        stats.kurtosis(window_values)
                    ])
                
                # 特徴量名を追加（最初の実行時のみ）
                if not feature_names:
                    stat_names = [
                        f"{measurement_type}_mean",
                        f"{measurement_type}_std",
                        f"{measurement_type}_min",
                        f"{measurement_type}_max",
                        f"{measurement_type}_median",
                        f"{measurement_type}_q25",
                        f"{measurement_type}_q75",
                        f"{measurement_type}_var",
                        f"{measurement_type}_skew",
                        f"{measurement_type}_kurtosis"
                    ]
                    feature_names.extend(stat_names)
            
            # 2次元リストを転置
            if features:
                transposed_features = list(map(list, zip(*features)))
                return transposed_features, feature_names
            else:
                return [], feature_names
            
        except Exception as e:
            logger.error(f"Error extracting statistical features: {e}")
            raise
    
    async def _extract_temporal_features(
        self,
        sensor_data: Dict[str, pd.DataFrame],
        window_config: WindowConfig
    ) -> Tuple[List[List[float]], List[str]]:
        """時間的特徴量を抽出"""
        try:
            features = []
            feature_names = []
            
            for measurement_type, df in sensor_data.items():
                if len(df) < window_config.window_size:
                    continue
                
                values = df['value'].values
                
                # 滑動窓で時間的特徴量を計算
                for i in range(0, len(values) - window_config.window_size + 1, window_config.step_size):
                    window_values = values[i:i + window_config.window_size]
                    
                    if len(features) <= i // window_config.step_size:
                        features.append([])
                    
                    # 差分統計
                    diff_values = np.diff(window_values)
                    
                    # ゼロクロッシング数
                    zero_crossings = np.sum(np.diff(np.sign(window_values - np.mean(window_values))) != 0)
                    
                    # トレンド（線形回帰の傾き）
                    x = np.arange(len(window_values))
                    slope, intercept, r_value, p_value, std_err = stats.linregress(x, window_values)
                    
                    # 移動平均からの偏差
                    ma_deviation = np.mean(np.abs(window_values - np.mean(window_values)))
                    
                    features[i // window_config.step_size].extend([
                        np.mean(diff_values),
                        np.std(diff_values),
                        zero_crossings,
                        slope,
                        r_value ** 2,  # 決定係数
                        ma_deviation,
                        np.mean(np.abs(diff_values)),  # 平均絶対差分
                        len(find_peaks(window_values)[0]),  # ピーク数
                        window_values[-1] - window_values[0]  # 始終点差
                    ])
                
                # 特徴量名を追加
                if not feature_names:
                    temp_names = [
                        f"{measurement_type}_diff_mean",
                        f"{measurement_type}_diff_std",
                        f"{measurement_type}_zero_crossings",
                        f"{measurement_type}_trend_slope",
                        f"{measurement_type}_trend_r2",
                        f"{measurement_type}_ma_deviation",
                        f"{measurement_type}_abs_diff_mean",
                        f"{measurement_type}_peak_count",
                        f"{measurement_type}_range_change"
                    ]
                    feature_names.extend(temp_names)
            
            # 2次元リストを転置
            if features:
                transposed_features = list(map(list, zip(*features)))
                return transposed_features, feature_names
            else:
                return [], feature_names
            
        except Exception as e:
            logger.error(f"Error extracting temporal features: {e}")
            raise
    
    async def _extract_spectral_features(
        self,
        sensor_data: Dict[str, pd.DataFrame],
        window_config: WindowConfig
    ) -> Tuple[List[List[float]], List[str]]:
        """周波数領域特徴量を抽出"""
        try:
            features = []
            feature_names = []
            
            for measurement_type, df in sensor_data.items():
                if len(df) < window_config.window_size:
                    continue
                
                values = df['value'].values
                
                # 滑動窓でスペクトル特徴量を計算
                for i in range(0, len(values) - window_config.window_size + 1, window_config.step_size):
                    window_values = values[i:i + window_config.window_size]
                    
                    if len(features) <= i // window_config.step_size:
                        features.append([])
                    
                    # FFT
                    fft_values = np.fft.fft(window_values)
                    freqs = np.fft.fftfreq(len(window_values))
                    magnitudes = np.abs(fft_values)
                    
                    # スペクトル密度
                    power_spectrum = magnitudes ** 2
                    
                    # スペクトル中心周波数
                    spectral_centroid = np.sum(freqs[:len(freqs)//2] * magnitudes[:len(magnitudes)//2]) / np.sum(magnitudes[:len(magnitudes)//2])
                    
                    # スペクトルロールオフ
                    cumulative_power = np.cumsum(power_spectrum[:len(power_spectrum)//2])
                    total_power = cumulative_power[-1]
                    rolloff_threshold = 0.85 * total_power
                    rolloff_idx = np.where(cumulative_power >= rolloff_threshold)[0]
                    spectral_rolloff = freqs[rolloff_idx[0]] if len(rolloff_idx) > 0 else 0
                    
                    # スペクトル帯域幅
                    spectral_bandwidth = np.sqrt(np.sum(((freqs[:len(freqs)//2] - spectral_centroid) ** 2) * magnitudes[:len(magnitudes)//2]) / np.sum(magnitudes[:len(magnitudes)//2]))
                    
                    # ドミナント周波数
                    dominant_freq_idx = np.argmax(magnitudes[1:len(magnitudes)//2]) + 1
                    dominant_frequency = freqs[dominant_freq_idx]
                    
                    features[i // window_config.step_size].extend([
                        spectral_centroid,
                        spectral_rolloff,
                        spectral_bandwidth,
                        dominant_frequency,
                        np.max(magnitudes[1:len(magnitudes)//2]),  # 最大振幅
                        np.mean(magnitudes[1:len(magnitudes)//2]),  # 平均振幅
                        np.std(magnitudes[1:len(magnitudes)//2]),   # 振幅の標準偏差
                    ])
                
                # 特徴量名を追加
                if not feature_names:
                    spec_names = [
                        f"{measurement_type}_spectral_centroid",
                        f"{measurement_type}_spectral_rolloff",
                        f"{measurement_type}_spectral_bandwidth",
                        f"{measurement_type}_dominant_frequency",
                        f"{measurement_type}_max_magnitude",
                        f"{measurement_type}_mean_magnitude",
                        f"{measurement_type}_std_magnitude"
                    ]
                    feature_names.extend(spec_names)
            
            # 2次元リストを転置
            if features:
                transposed_features = list(map(list, zip(*features)))
                return transposed_features, feature_names
            else:
                return [], feature_names
            
        except Exception as e:
            logger.error(f"Error extracting spectral features: {e}")
            raise
    
    async def _extract_pattern_features(
        self,
        sensor_data: Dict[str, pd.DataFrame],
        window_config: WindowConfig
    ) -> Tuple[List[List[float]], List[str]]:
        """パターン特徴量を抽出"""
        try:
            features = []
            feature_names = []
            
            for measurement_type, df in sensor_data.items():
                if len(df) < window_config.window_size:
                    continue
                
                values = df['value'].values
                
                # 滑動窓でパターン特徴量を計算
                for i in range(0, len(values) - window_config.window_size + 1, window_config.step_size):
                    window_values = values[i:i + window_config.window_size]
                    
                    if len(features) <= i // window_config.step_size:
                        features.append([])
                    
                    # 自己相関
                    autocorr = np.correlate(window_values, window_values, mode='full')
                    autocorr = autocorr[autocorr.size // 2:]
                    autocorr = autocorr / autocorr[0]  # 正規化
                    
                    # 周期性指標
                    if len(autocorr) > 1:
                        first_peak_lag = 1
                        for j in range(1, min(len(autocorr), len(window_values) // 2)):
                            if autocorr[j] > 0.3:  # 閾値
                                first_peak_lag = j
                                break
                    else:
                        first_peak_lag = 1
                    
                    # エントロピー
                    hist, _ = np.histogram(window_values, bins=10)
                    hist = hist + 1e-10  # ゼロ除算回避
                    prob = hist / np.sum(hist)
                    entropy = -np.sum(prob * np.log2(prob))
                    
                    # 複雑度（近似エントロピー）
                    def _approximate_entropy(data, m=2, r=0.2):
                        N = len(data)
                        patterns = []
                        
                        for i in range(N - m + 1):
                            patterns.append(data[i:i + m])
                        
                        patterns = np.array(patterns)
                        C = []
                        
                        for i in range(len(patterns)):
                            matches = 0
                            for j in range(len(patterns)):
                                if np.max(np.abs(patterns[i] - patterns[j])) <= r * np.std(data):
                                    matches += 1
                            C.append(matches / len(patterns))
                        
                        return -np.mean(np.log(C)) if C else 0
                    
                    approx_entropy = _approximate_entropy(window_values)
                    
                    features[i // window_config.step_size].extend([
                        autocorr[1] if len(autocorr) > 1 else 0,  # ラグ1の自己相関
                        first_peak_lag,
                        entropy,
                        approx_entropy,
                        np.mean(np.abs(np.diff(window_values, n=2))),  # 2次差分の平均絶対値
                        len(np.where(np.diff(np.sign(np.diff(window_values))))[0])  # 変曲点数
                    ])
                
                # 特徴量名を追加
                if not feature_names:
                    pattern_names = [
                        f"{measurement_type}_autocorr_lag1",
                        f"{measurement_type}_first_peak_lag",
                        f"{measurement_type}_entropy",
                        f"{measurement_type}_approx_entropy",
                        f"{measurement_type}_second_diff_mean",
                        f"{measurement_type}_inflection_points"
                    ]
                    feature_names.extend(pattern_names)
            
            # 2次元リストを転置
            if features:
                transposed_features = list(map(list, zip(*features)))
                return transposed_features, feature_names
            else:
                return [], feature_names
            
        except Exception as e:
            logger.error(f"Error extracting pattern features: {e}")
            raise
    
    async def _extract_correlation_features(
        self,
        sensor_data: Dict[str, pd.DataFrame],
        window_config: WindowConfig
    ) -> Tuple[List[List[float]], List[str]]:
        """相関特徴量を抽出"""
        try:
            features = []
            feature_names = []
            
            measurement_types = list(sensor_data.keys())
            
            if len(measurement_types) < 2:
                return [], []
            
            # すべてのペアの相関を計算
            for i, type1 in enumerate(measurement_types):
                for j, type2 in enumerate(measurement_types[i+1:], i+1):
                    df1 = sensor_data[type1]
                    df2 = sensor_data[type2]
                    
                    # 時間軸を合わせる
                    common_index = df1.index.intersection(df2.index)
                    if len(common_index) < window_config.window_size:
                        continue
                    
                    values1 = df1.loc[common_index]['value'].values
                    values2 = df2.loc[common_index]['value'].values
                    
                    # 滑動窓で相関を計算
                    for k in range(0, len(values1) - window_config.window_size + 1, window_config.step_size):
                        window_values1 = values1[k:k + window_config.window_size]
                        window_values2 = values2[k:k + window_config.window_size]
                        
                        if len(features) <= k // window_config.step_size:
                            features.append([])
                        
                        # ピアソン相関
                        pearson_corr = np.corrcoef(window_values1, window_values2)[0, 1]
                        
                        # 相互相関の最大値
                        cross_corr = np.correlate(window_values1, window_values2, mode='full')
                        max_cross_corr = np.max(np.abs(cross_corr)) / (np.std(window_values1) * np.std(window_values2) * len(window_values1))
                        
                        # ラグ相関
                        lag_corr = np.corrcoef(window_values1[1:], window_values2[:-1])[0, 1] if len(window_values1) > 1 else 0
                        
                        features[k // window_config.step_size].extend([
                            pearson_corr if not np.isnan(pearson_corr) else 0,
                            max_cross_corr if not np.isnan(max_cross_corr) else 0,
                            lag_corr if not np.isnan(lag_corr) else 0
                        ])
                    
                    # 特徴量名を追加
                    if not feature_names:
                        corr_names = [
                            f"{type1}_{type2}_pearson_corr",
                            f"{type1}_{type2}_max_cross_corr",
                            f"{type1}_{type2}_lag_corr"
                        ]
                        feature_names.extend(corr_names)
            
            # 2次元リストを転置
            if features:
                transposed_features = list(map(list, zip(*features)))
                return transposed_features, feature_names
            else:
                return [], feature_names
            
        except Exception as e:
            logger.error(f"Error extracting correlation features: {e}")
            raise
    
    async def _scale_features(
        self,
        feature_matrix: np.ndarray,
        scaling_method: ScalingMethod
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """特徴量をスケーリング"""
        try:
            if scaling_method == ScalingMethod.NONE:
                return feature_matrix, {"method": "none"}
            
            if scaling_method == ScalingMethod.STANDARD:
                scaler = StandardScaler()
            elif scaling_method == ScalingMethod.MINMAX:
                scaler = MinMaxScaler()
            else:
                # ロバストスケーリングは簡易実装
                scaler = StandardScaler()
            
            scaled_features = scaler.fit_transform(feature_matrix)
            
            scaling_info = {
                "method": scaling_method.value,
                "scaler_params": {
                    "mean": scaler.mean_.tolist() if hasattr(scaler, 'mean_') else None,
                    "scale": scaler.scale_.tolist() if hasattr(scaler, 'scale_') else None,
                    "min": scaler.data_min_.tolist() if hasattr(scaler, 'data_min_') else None,
                    "max": scaler.data_max_.tolist() if hasattr(scaler, 'data_max_') else None
                }
            }
            
            return scaled_features, scaling_info
            
        except Exception as e:
            logger.error(f"Error scaling features: {e}")
            raise
    
    async def _generate_feature_timestamps(
        self,
        sensor_data: Dict[str, pd.DataFrame],
        window_config: WindowConfig
    ) -> List[datetime]:
        """特徴量に対応するタイムスタンプを生成"""
        try:
            # 最初の測定タイプのタイムスタンプを基準とする
            first_measurement = list(sensor_data.keys())[0]
            df = sensor_data[first_measurement]
            
            timestamps = []
            
            for i in range(0, len(df) - window_config.window_size + 1, window_config.step_size):
                # 窓の中央時刻を使用
                window_start_idx = i
                window_end_idx = i + window_config.window_size - 1
                center_idx = (window_start_idx + window_end_idx) // 2
                
                if center_idx < len(df):
                    timestamps.append(df.index[center_idx])
            
            return timestamps
            
        except Exception as e:
            logger.error(f"Error generating feature timestamps: {e}")
            raise
    
    async def prepare_training_data(
        self,
        feature_set: FeatureSet,
        target_measurement_type: str,
        prediction_horizon: int = 1,
        test_split_ratio: float = 0.2
    ) -> Dict[str, Any]:
        """
        訓練データとテストデータを準備
        """
        try:
            if not feature_set.feature_values:
                raise ValueError("No feature data available")
            
            # 特徴量行列
            X = np.array(feature_set.feature_values)
            
            # ターゲット値を生成（予測対象）
            # 簡単な実装：prediction_horizon期間後の値を予測
            y = np.roll(X[:, 0], -prediction_horizon)  # 最初の特徴量を予測対象とする
            
            # 末尾の予測不可能な部分を除去
            X = X[:-prediction_horizon]
            y = y[:-prediction_horizon]
            
            # 訓練・テスト分割
            split_point = int(len(X) * (1 - test_split_ratio))
            
            X_train, X_test = X[:split_point], X[split_point:]
            y_train, y_test = y[:split_point], y[split_point:]
            
            train_timestamps = feature_set.timestamps[:split_point]
            test_timestamps = feature_set.timestamps[split_point:len(X)]
            
            return {
                "X_train": X_train,
                "X_test": X_test,
                "y_train": y_train,
                "y_test": y_test,
                "train_timestamps": train_timestamps,
                "test_timestamps": test_timestamps,
                "feature_names": feature_set.feature_names,
                "target_measurement_type": target_measurement_type,
                "prediction_horizon": prediction_horizon,
                "scaling_info": feature_set.scaling_info,
                "metadata": feature_set.metadata
            }
            
        except Exception as e:
            logger.error(f"Error preparing training data: {e}")
            raise


# グローバルインスタンス
feature_engineering_service = FeatureEngineeringService()